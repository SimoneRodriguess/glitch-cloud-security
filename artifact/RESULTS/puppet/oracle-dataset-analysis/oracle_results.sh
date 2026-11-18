if test -f "dump.csv"; then
	rm dump.csv
fi

if test -f "../SLIC_Puppet/SLIC/dump.csv"; then
	rm ../SLIC_Puppet/SLIC/dump.csv
fi

#rm dump.csv
#rm ../SLIC_Puppet/SLIC/dump.csv

echo "Running SLIC on the oracle dataset..."
(cd /RESULTS/puppet/SLIC_Puppet/SLIC; python3 main.py ../../oracle-dataset count.csv dump.csv 2> /dev/null)
mv ../SLIC_Puppet/SLIC/count.csv .
mv ../SLIC_Puppet/SLIC/dump.csv .
rm count.csv
rm TMP.LOG

echo "Calculating the precision and recall results..."
echo ""
echo "======== SLIC RESULTS ========"
python3 fix_slic_dataset.py
python3 calculate-metrics.py dump.csv 
cp dump.csv new/SLIC-puppet-oracle.csv
rm dump.csv

echo "Running GLITCH with the SLIC configuration on the oracle dataset..."
glitch --tech puppet --csv --smells security --config ../../../GLITCH/configs/SLIC_puppet.ini ../oracle-dataset dump.csv 2> /dev/null

echo "Calculating the precision and recall results..."
echo ""
echo "====== GLITCH (SLIC) RESULTS ========"
python3 fix_glitch_dataset.py
python3 calculate-metrics.py dump.csv 
cp dump.csv new/GLITCH-SLIC-puppet-oracle.csv
rm dump.csv

echo "Running GLITCH with the improved configuration on the oracle dataset..."
glitch --tech puppet --csv --smells security --config ../../../GLITCH/configs/improved.ini ../oracle-dataset dump.csv 2> /dev/null

echo "Calculating the precision and recall results..."
echo ""
echo "====== GLITCH improved RESULTS ========"
python3 fix_glitch_dataset.py
python3 calculate-metrics.py dump.csv 
cp dump.csv new/GLITCH-puppet-oracle.csv
rm dump.csv
