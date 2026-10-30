#!/bin/bash
python generate_instances.py
python ids.py -i ./instances/data_generated.txt -o ./results/report_ids_generated.csv
python ids.py -i ./instances/data.txt -o ./results/report_ids_benchmark.csv
python weighted_a_star.py
python run_experiments.py