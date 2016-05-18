cd data
sftp last@felixlast.de <<EOF
get wave-forecast/output/*.csv
rm wave-forecast/output/*.csv
EOF
git add *.csv
git commit -m 'Pull new data'
git push origin master
