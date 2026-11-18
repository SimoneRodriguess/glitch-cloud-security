if test -f "dump.csv"; then
	rm dump.csv
fi

echo "Running SLAC on the oracle dataset..."
python3 ../SLAC_Ansible.py ../oracle-dataset
rm ansible-smell-count.csv

echo "Calculating the precision and recall results..."
echo ""
echo "======== SLAC RESULTS ========"
python3 fix_slac_dataset.py
python3 calculate-metrics.py dump.csv
cp dump.csv new/SLAC-ansible-oracle.csv
rm dump.csv
echo ""

echo "Running GLITCH with the SLAC configuration on the oracle dataset..."
glitch --tech ansible --smells security --csv --dataset --config ../../../GLITCH/configs/SLAC_ansible.ini ../oracle-dataset dump.csv 2> /dev/null

echo "Calculating the precision and recall results..."
echo ""
echo "====== GLITCH (SLAC) RESULTS ========"
python3 fix_glitch_dataset.py
python3 calculate-metrics.py dump.csv
cp dump.csv new/GLITCH-SLAC-ansible-oracle.csv
rm dump.csv
echo ""

echo "Running GLITCH with the improved configuration on the oracle dataset..."
glitch --tech ansible --smells security --csv --dataset --config ../../../GLITCH/configs/improved.ini ../oracle-dataset dump.csv 2> /dev/null

echo "Calculating the precision and recall results..."
echo ""
echo "====== GLITCH improved RESULTS ========"
python3 fix_glitch_dataset.py
python3 calculate-metrics.py dump.csv
cp dump.csv new/GLITCH-ansible-oracle.csv
rm dump.csv
echo ""
