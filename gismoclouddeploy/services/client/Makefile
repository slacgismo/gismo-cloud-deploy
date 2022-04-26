.PHONY: 
process_files:
	@echo "process files"
	docker exec -it web python app.py process_files "pv.insight.nrel" "['PVO/PVOutput/10059.csv','PVO/PVOutput/10010.csv']" "['Power(W)'','W']" "['MOSEK']"

.PHONY: 
process_multi_files:
	@echo "process folder"
	docker exec -it web python app.py process_multi_files "pv.insight.nrel" "PVO/PVOutput/10059.csv,PVO/PVOutput/10010.csv" "Power(W),W" "MOSEK"

.PHONY: 
import_yml:
	@echo "import from yml"
	bash read_yaml.sh
