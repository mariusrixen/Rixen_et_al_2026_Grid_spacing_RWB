for ens in $(seq 0 0); do
    ens_padded=$(printf "%03d" "$ens")
    echo "=== Starting ensemble ${ens_padded} ==="
    
    export ENS_NUM=${ens}
    export ENS_NUM_PADDED=${ens_padded}
    
    python launch_Lagranto_R02B10_ens.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Ensemble ${ens_padded} completed successfully."
    else
        echo "⚠️ Ensemble ${ens_padded} failed."
    fi
    
    echo "---------------------------------------------"
done

echo "🎯 All ensembles completed."