
ls -trlh ../../tmp/ | awk '{print $7" "$8" "$9}' | sed "s/:/ /g" | awk '{a=($1*24+$2)*60+$3; print a" "$4}' > files
now=`date | awk '{print $3" "$4}' | sed "s/:/ /g" | awk '{print ($1*24+$2)*60+$3}'`;
cat files | awk -v now="$now" '{if($1<(now-20))print $2}' > remove-them
for i in `cat remove-them`; do rm -f ../../tmp/$i;done
rm files remove-them

:<<"CMT"
for i in data/single-flow-scenario-*/tcpdatagen_mm_*.log;
do
    rm $i
done
for i in data/single-flow-scenario-*/*_mm_*.log;
do
    rm $i
done
CMT

mv data/* /mydata/ccbench-logs/
mv ../../third_party/tcpdatagen/dataset/* /mydata/ccbench-traces/
