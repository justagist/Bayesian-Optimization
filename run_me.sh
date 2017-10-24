#!/bin/sh
# Use only one thread per python call
export OMP_NUM_THREADS=1
# Disable TensorFlow warnings
export TF_CPP_MIN_LOG_LEVEL=2
# Delete old results
rm -rf out/*_*

# Figure 1
python gp_posteriors.py --plot_posteriors=1 --seed=130 --num_seeds=1 --batch_size=3 --opt_restarts=500

# Figure 2
# Run the experiments
for algorithm in 'OEI' 'QEI' 'QEI_CL' 'LP_EI'; do
    num_seeds=200
	threads=40
	seeds_per_thread=$((num_seeds/threads))
	thread=0
	while [  $thread -lt $threads ]; do
		start=$(($seed_start+$thread*$seeds_per_thread))

		python gp_posteriors.py --algorithm=$algorithm --seed=$start --num_seeds=$seeds_per_thread &

		thread=$(($thread+1))
	done
	wait
    # python gp_posteriors.py --algorithm=$algorithm --num_seeds=200
done
# Create the plot
python plot_ei_vs_batch.py out/gp_OEI out/gp_QEI out/gp_QEI_CL out/gp_LP_EI

# Figure 3
python gp_posteriors.py --algorithm='QEI' --plot_problem=1 --batch_size=5 --opt_restarts=500


# Figure 4
# Run the experiments
for function in 'branin' 'cosines' 'sixhumpcamel' 'loghart6'; do
    if [ $function == 'loghart6' ]; then
        initial_size=20 
        iterations=20
    else
        initial_size=5
        iterations=7
    fi
    for algorithm in 'QEI' 'LP_EI' 'BLCB' 'Random'; do
        num_seeds=40
        threads=40
        seeds_per_thread=$((num_seeds/threads))
        thread=0
        while [  $thread -lt $threads ]; do
            start=$(($seed_start+$thread*$seeds_per_thread))

            python run.py --seed=$start --function=$function --algorithm=$algorithm --initial_size=$initial_size --iterations=$iterations --noise=1e-6 --num_seeds=$seeds_per_thread &

            thread=$(($thread+1))
        done
        wait
        # python run.py --function=$function --algorithm=$algorithm --initial_size=$initial_size --iterations=$iterations --noise=1e-6 --num_seeds=40
    done
    num_seeds=40
    threads=40
    seeds_per_thread=$((num_seeds/threads))
    thread=0
    while [  $thread -lt $threads ]; do
        start=$(($seed_start+$thread*$seeds_per_thread))

        python run.py --seed=$start --function=$function --algorithm='OEI' --initial_size=$initial_size --iterations=$iterations --noise=1e-6 --num_seeds=$seeds_per_thread --samples=100 --priors=1 &

        thread=$(($thread+1))
    done
    wait
    # python run.py --function=$function --algorithm='OEI' --initial_size=$initial_size --iterations=$iterations --noise=1e-6 --num_seeds=40 --samples=100 --priors=1
done
# Create the plots
python plot_experiments.py branin out/branin_OEI out/branin_QEI out/branin_BLCB out/branin_LP_EI out/branin_Random --linewidth=2 --capsize=5
python plot_experiments.py cosines out/cosines_OEI out/cosines_QEI out/cosines_BLCB out/cosines_LP_EI out/cosines_Random --linewidth=2 --capsize=5
python plot_experiments.py sixhumpcamel out/sixhumpcamel_OEI out/sixhumpcamel_QEI out/sixhumpcamel_BLCB out/sixhumpcamel_LP_EI out/sixhumpcamel_Random --linewidth=2 --capsize=5
python plot_experiments.py loghart6 out/loghart6_OEI out/loghart6_QEI out/loghart6_BLCB out/loghart6_LP_EI out/loghart6_Random --linewidth=2 --capsize=5 --sizex=10

tar -zcf output.tgz out log results run_me.sh
mv output.tgz ~/
