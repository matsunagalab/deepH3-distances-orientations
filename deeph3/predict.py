import torch
import torch.nn as nn
from deeph3 import H3ResNet
from deeph3.util import get_probs_from_model, bin_matrix
from os.path import isfile


def predict(model, fasta_file, chain_delimiter=True, binning_method='max'):
    """
    Predicts the binned version of a distance matrix
    """
    probs = get_probs_from_model(model, fasta_file, chain_delimiter=chain_delimiter)
    dist, omega, theta, phi = bin_matrix(probs, are_logits=False,
                                         method=binning_method)
    return dict(distance_matrix=dist, omega_matrix=omega,
                theta_matrix=theta, phi_matrix=phi)


def load_model(file_name, num_blocks1D=3, num_blocks2D=21):
    """Loads a model from a correctly named file"""
    if not isfile(file_name):
        raise FileNotFoundError(f'No file at {file_name}')
    checkpoint_dict = torch.load(file_name, map_location='cpu')
    model_state = checkpoint_dict['model_state_dict']

    dilation_cycle = 0 if not 'dilation_cycle' in checkpoint_dict else checkpoint_dict[
        'dilation_cycle']

    in_layer = list(model_state.keys())[0]
    out_layer = list(model_state.keys())[-1]
    num_out_bins = model_state[out_layer].shape[0]
    in_planes = model_state[in_layer].shape[1]

    if 'num_blocks1D' in checkpoint_dict:
        num_blocks1D = checkpoint_dict['num_blocks1D']
    if 'num_blocks2D' in checkpoint_dict:
        num_blocks2D = checkpoint_dict['num_blocks2D']

    resnet = H3ResNet(in_planes=in_planes, num_out_bins=num_out_bins,
                      num_blocks1D=num_blocks1D, num_blocks2D=num_blocks2D,
                      dilation_cycle=dilation_cycle)
    model = nn.Sequential(resnet)
    model.load_state_dict(model_state)
    model.eval()

    return model


if __name__ == '__main__':
    import argparse
    import pickle
    import os

    predict_py_path = os.path.dirname(os.path.realpath(__file__))
    default_model_path = os.path.join(predict_py_path, 'models/fully_trained_model.p')
    default_fasta_path = os.path.join(predict_py_path, 'data/antibody_dataset/fastas_testrun/1a0q_trunc.fasta')

    desc = (
        '''
        Outputs the logits for a given fasta file for an antibody that is structured as such:
            >[PDB ID]:H	[heavy chain sequence length]
            [heavy chain sequence]
            >[PDB ID]:L	[light chain sequence length]
            [light chain sequence]
        See 1a0q_trunc.fasta for an example.
        ''')
    parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--model_file', type=str,
                        default=default_model_path,
                        help=('A pickle file containing a dictionary with the following keys:\n'
                              '    state_dict: The state dict of the H3ResNet model\n'
                              '    num_blocks1D: The number of one dimensional ResNet blocks\n'
                              '    num_blocks2D: The number of two dimensional ResNet blocks\n'
                              '    dilation (optional): The dilation cycle of the model'))
    parser.add_argument('--fasta_file', type=str,
                        default=default_fasta_path,
                        help='The fasta file used for prediction.')
    parser.add_argument('--out_file', type=str,
                        default='model_out.p',
                        help='The pickle file to save the model output to.')
    args = parser.parse_args()
    model = load_model(args.model_file)
    pickle.dump(predict(model, args.fasta_file), open(args.out_file, 'wb'))

