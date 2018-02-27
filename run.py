from __future__ import print_function
import os
import numpy as np
import tensorflow as tf
import random
import argparse
import gpflow
import GPy
import GPyOpt
import methods
import time
import pickle
from test_functions import benchmark_functions, scale_function
import copy
from kernel import NN, SafeMatern52, SafeMatern32

algorithms = {
    'OEI': methods.OEI,
    'QEI': methods.QEI,
    'QEI_CL': methods.QEI_CL,
    'LP_EI': methods.LP_EI,
    'BLCB': methods.BLCB,
    'Random_EI': methods.Random_EI,
    'Random': methods.Random
}


def run(options, seed, robust=False, save=False):
    options['seed'] = seed
    # Set random seed: Numpy, Tensorflow, Python 
    tf.reset_default_graph()
    tf.set_random_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    bo = algorithms[options['algorithm']](options)

    try:
        start = time.time()
        X, Y = bo.bayesian_optimization()
        end = time.time()
        print('Done with:', bo.options['job_name'], 'seed:', seed,
              'Time:', '%.2f' % ((end - start)/60), 'min')
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, stopping.")
        raise
    except:
        print('Experiment of', bo.options['job_name'],
              'with seed', seed, 'failed')
        X, Y = None, None
        if not robust:
            raise

    if save:
        save_folder = 'out/' + bo.options['job_name'] + '/'
        filepath = save_folder + str(seed) + '.npz'
        try:
            os.makedirs(save_folder)
        except OSError:
            pass
        try:
            os.remove(filepath)
        except OSError:
            pass

        np.savez(filepath, X=X, Y=Y)


def create_options(args):
    functions = {
        'branin': GPyOpt.objective_examples.experiments2d.branin(),
        'cosines': GPyOpt.objective_examples.experiments2d.cosines(),
        'sixhumpcamel': GPyOpt.objective_examples.experiments2d.sixhumpcamel(),
        'eggholder': GPyOpt.objective_examples.experiments2d.eggholder(),
        'alpine1': GPyOpt.objective_examples.experimentsNd.alpine1(input_dim=5),
        'hart6': benchmark_functions.hart6(),
        'loghart6': benchmark_functions.loghart6(),
        'RoboschoolHopper-v1': benchmark_functions.ppo(experiment='RoboschoolHopper-v1'),
        'RoboschoolInvertedDoublePendulum-v1': benchmark_functions.ppo(experiment='RoboschoolInvertedDoublePendulum-v1'),
        'RoboschoolInvertedPendulumSwingup-v1': benchmark_functions.ppo(experiment='RoboschoolInvertedPendulumSwingup-v1'),
        'RoboschoolInvertedPendulum-v1': benchmark_functions.ppo(experiment='RoboschoolInvertedPendulum-v1'),
        'RoboschoolReacher-v1': benchmark_functions.ppo(experiment='RoboschoolReacher-v1'),
    }

    kernels_gpflow = {
        'RBF': gpflow.kernels.RBF,
        'Matern32': SafeMatern32,
        'Matern52': SafeMatern52
    }

    kernels_gpy = {
        'RBF': GPy.kern.RBF,
        'Matern32': GPy.kern.Matern32,
        'Matern52': GPy.kern.Matern52
    }

    options = vars(copy.copy(args))
    options['objective'] = functions[options['function']]
    options['objective'].bounds = np.asarray(options['objective'].bounds)
    options['objective'] = scale_function(options['objective'])

    input_dim = options['objective'].bounds.shape[0]
    if options['algorithm'] != 'LP_EI':
        k1 = kernels_gpflow[options['kernel']](
            input_dim=input_dim, ARD=options['ard'])
        k1_ = kernels_gpflow[options['kernel']](
            input_dim=input_dim, ARD=options['ard'])
        if options['priors']:
            k1.lengthscales.prior = gpflow.priors.Gamma(shape=2, scale=0.5)
            k1.variance.prior = gpflow.priors.Gaussian(mu=1, var=2)
            k1_.lengthscales.prior = gpflow.priors.Gamma(shape=2, scale=0.5)
            k1_.variance.prior = gpflow.priors.Gaussian(mu=1, var=2)
        if options['NN'] == 0:
            options['kernel'] = k1
        else:
            k2 = NN(input_dim=input_dim, ARD=True) # options['ard'])
            options['kernel'] = k1 + k2

        if options['samples'] > 0:
            assert options['priors']
    else:
        options['kernel'] = kernels_gpy[options['kernel']](
            input_dim=input_dim, ARD=options['ard']
        )

    options['job_name'] = options['function'] + '_' + options['algorithm']
    if options['NN']:
        options['job_name'] = options['job_name'] + '-new'

    return options


def main(args):
    options = create_options(args)

    # Save command line arguments
    save_folder = 'out/' + options['job_name'] + '/'
    filepath = save_folder + 'arguments.pkl'
    try:
        os.makedirs(save_folder)
    except OSError:
        pass

    try:
        os.remove(filepath)
    except OSError:
        pass
    try:
        with open(filepath, 'wb') as file:
            pickle.dump(args, file, pickle.HIGHEST_PROTOCOL)
    except OSError:
        pass

    filepath = save_folder + 'fmin.txt'
    try:
        fmin = options['objective'].fmin
    except AttributeError:
        fmin = 0
    np.savetxt(filepath, np.array([fmin]))

    for seed in range(args.seed, args.seed + args.num_seeds):
        run(options, seed=seed, save=options['save'])


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--function', default='branin')
    parser.add_argument('--algorithm', default='OEI')
    parser.add_argument('--seed', type=int, default=123)
    parser.add_argument('--num_seeds', type=int, default=1)
    parser.add_argument('--save', type=int, default=1)

    parser.add_argument('--samples', type=int, default=0)
    parser.add_argument('--priors', type=int, default=0)

    parser.add_argument('--batch_size', type=int, default=5)
    parser.add_argument('--iterations', type=int, default=10)
    parser.add_argument('--initial_size', type=int, default=10)
    parser.add_argument('--init_replicates', type=int, default=0)
    parser.add_argument('--model_restarts', type=int, default=20)
    parser.add_argument('--opt_restarts', type=int, default=20)
    parser.add_argument('--normalize_Y', type=int, default=1)
    parser.add_argument('--noise', type=float)
    parser.add_argument('--kernel', default='Matern32')
    parser.add_argument('--ard', type=int, default=0)
    parser.add_argument('--nl_solver',  default='scipy')
    parser.add_argument('--hessian', type=int, default=0)
    parser.add_argument('--NN', type=int, default=0)

    parser.add_argument('--beta_multiplier', type=float, default=.1)
    parser.add_argument('--delta', type=float, default=.1)
    parser.add_argument('--liar_choice', default='mean')

    return parser


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    main(args)
