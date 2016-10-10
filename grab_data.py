# coding: utf-8
import requests
import json
import datetime
import pandas as pd
from pandas.io.json import json_normalize
import dateutil.parser

def explanatory():
    api_key = 'cb6e9e04-daa4-4e54-9589-7815988c8792'
    # get last available data time
    capabilities_api = 'http://datapoint.metoffice.gov.uk/public/data/val/wxmarineobs/all/json/capabilities?res=hourly&key=' + api_key
    capabilities_res = requests.get(capabilities_api)
    capabilities_res = json.loads(capabilities_res.text)
    capabilities_res = capabilities_res['Resource']['TimeSteps']['TS']
    s_times = pd.Series(capabilities_res)

    marine_obs_api = 'http://datapoint.metoffice.gov.uk/public/data/val/wxmarineobs/all/json/62029?res=hourly&key=' + api_key
    marine_obs_res = requests.get(marine_obs_api)
    marine_obs_res = json.loads(marine_obs_res.text)
    days = marine_obs_res['SiteRep']['DV']['Location']['Period']
    day_1 = days[0]['Rep']
    df_day1 = json_normalize(day_1)
    if len(days) > 1:
        day_2 = days[1]['Rep']
        df_day2 = json_normalize(day_2)
    else:
        df_day2 = df_day1.iloc[0:0]
    df_days = pd.concat([df_day1, df_day2], ignore_index=True)
    column_name_mapping = {feature['name'] : feature['$'].lower().replace(" ", "_") for feature in marine_obs_res['SiteRep']['Wx']['Param']  }
    df_days.rename(columns=column_name_mapping, inplace=True)

    # for some reason, the capability API has more dates available - unclear!
    first_entry_hour = int(int(df_days.iloc[0][0]) / 60)
    last_entry_hour = int(int(df_days.iloc[-1][0]) / 60)
    if len(df_days) != len(s_times):
        s_times_conv = [dateutil.parser.parse(dt) for dt in s_times]
        first_corresponding_index = next( i for i,dt in enumerate(s_times_conv) if dt.hour == first_entry_hour )
        last_corresponding_index = len(s_times_conv) - next( i for i,dt in enumerate(reversed(s_times_conv)) if dt.hour == last_entry_hour )
        s_times_fixed = pd.Series([dt.isoformat() for dt in s_times_conv[first_corresponding_index:last_corresponding_index]])
        s_times_fixed.index = range(len(s_times_fixed))
    else:
        s_times_fixed = s_times

    df_days.index = pd.DatetimeIndex(s_times_fixed, freq='H')
    return df_days

def target(days=5):
    surfline_api = 'http://api.surfline.com/v1/forecasts/{SPOT_ID}?resources=surf&days={DAYS}&getAllSpots=false&units=e&interpolate=false&showOptimal=false'
    spot_id = 44509 # Costa da Caparica
    surf_report_res = requests.get(surfline_api.replace("{SPOT_ID}",str(spot_id)).replace("{DAYS}",str(days)))
    surf_report_json = json.loads(surf_report_res.text)
    surf_report_json = surf_report_json['Surf']

    # The surfline result shows 4 data points for today. In Surf we can find a number of interesting attributes, including:
    #
    # - **dateStamp**: for which times have the conditions been predicted
    # - **surf_max**: maximum wave height in meters (possible target variable)
    # - **surf_min**: minimum wave height in meters
    # - **swell_direction1-3**: direction of the swell. unit unclear
    # - **swell_height1-3**: height of swell. unit unclear.
    # - **swell_period1-3**: period of swell. unit unclear.
    #
    # Each of these are an array of length 1 (= number of days requested), with arrays of four elements.
    # Let's remove the double array nesting to be able to create a data frame.

    df_surf = pd.DataFrame(columns=surf_report_json)
    for feature in surf_report_json:
        if type(surf_report_json[feature]) is list:
            merged_feature = []
            for sublist in surf_report_json[feature]:
                merged_feature += sublist
            df_surf[feature] = pd.Series(merged_feature)
    df_surf.index = pd.DatetimeIndex(df_surf['dateStamp'])
    #today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    #surfline_datetimes = [today.replace(hour=(1)), today.replace(hour=(7)), today.replace(hour=(13)), today.replace(hour=(19))]
    #df_surf.index = [datetime.datetime.isoformat(dt) + '+00:00' for dt in surfline_datetimes]

    target_var = 'surf_avg'
    s_target = pd.Series( ((df_surf['surf_max'] + df_surf['surf_min']) / 2)*0.3048, name=target_var )
    return s_target.resample('H').interpolate()