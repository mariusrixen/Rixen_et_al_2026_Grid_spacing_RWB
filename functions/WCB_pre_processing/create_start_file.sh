#!/bin/bash

# -------- Configuration --------
second_start=-30.0
second_end=-75.0
second_step=-1

third_start=30.0
third_end=50.0
third_step=1

fourth_start=100
fourth_end=2500
fourth_step=200

output_file="startf"

# -------- Clear output file --------
> "$output_file"

# -------- Helper function for float iteration --------
float_seq() {
    awk -v start="$1" -v end="$2" -v step="$3" 'BEGIN {
        for (i = start; (step > 0 ? i <= end : i >= end); i += step)
            printf "%.1f\n", i;
    }'
}

# -------- Generate data --------
for second in $(float_seq "$second_start" "$second_end" "$second_step"); do
    for third in $(float_seq "$third_start" "$third_end" "$third_step"); do
        for fourth in $(seq "$fourth_start" "$fourth_step" "$fourth_end"); do
            echo "0.00 $second $third $fourth" >> "$output_file"
	done
    done
done

echo "File '$output_file' created with grid data."

