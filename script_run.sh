#!/bin/bash
python generate_instances.py
python ids.py -i data_generated.txt -o report_ids_generated.csv
python ids.py -i data.txt -o report_ids_benchmark.csv
python W_A*.py
python run_experiments.py