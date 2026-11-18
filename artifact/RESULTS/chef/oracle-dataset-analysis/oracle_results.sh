if test -f "dump.csv"; then
	rm dump.csv
fi

if test -f "../SLAC_CHEF/SLIC/dump.csv"; then
	rm ../SLAC_CHEF/SLIC/dump.csv
fi

#rm dump.csv
#rm ../SLAC_CHEF/SLIC/dump.csv

echo "Running SLAC on the oracle dataset..."
(cd /RESULTS/chef/SLAC_Chef/SLIC/; python3 main.py ../../oracle-dataset count.csv dump.csv 2> /dev/null)
mv ../SLAC_Chef/SLIC/count.csv .
mv ../SLAC_Chef/SLIC/dump.csv .
rm count.csv
rm TMP.LOG

echo "Calculating the precision and recall results..."
echo ""
echo "======== SLAC RESULTS ========"
python3 fix_slac_dataset.py
python3 calculate-metrics.py dump.csv
cp dump.csv new/SLAC-chef-oracle.csv
rm dump.csv

echo "Running GLITCH with the SLAC configuration on the oracle dataset..."
glitch --tech chef --csv --smells security --config ../../../GLITCH/configs/SLAC_chef.ini ../oracle-dataset dump.csv 2> /dev/null

echo "Calculating the precision and recall results..."
echo ""
echo "====== GLITCH (SLAC) RESULTS ========"
python3 fix_glitch_dataset.py
python3 calculate-metrics.py dump.csv
cp dump.csv new/GLITCH-SLAC-chef-oracle.csv
rm dump.csv

echo "Running GLITCH with the improved configuration on the oracle dataset..."
glitch --tech chef --csv --smells security --config ../../../GLITCH/configs/improved.ini ../oracle-dataset dump.csv 2> /dev/null

echo "Calculating the precision and recall results..."
echo ""
echo "====== GLITCH improved RESULTS ========"
python3 fix_glitch_dataset.py
python3 calculate-metrics.py dump.csv
cp dump.csv new/GLITCH-chef-oracle.csv
rm dump.csv
