import os
import pickle
from subprocess import run
from threading import Thread
from typing import Dict, List

import numpy as np
import umap
from matplotlib import pyplot as plt
# noinspection PyUnresolvedReferences
from mpl_toolkits.mplot3d import Axes3D

DATASETS: Dict = {
    'mnist': 'https://www.dropbox.com/s/n3wurjt8v9qi6nc/mnist.mat?dl=0',
    'cover': 'https://www.dropbox.com/s/awx8iuzbu8dkxf1/cover.mat?dl=0',
    'letter': 'https://www.dropbox.com/s/rt9i95h9jywrtiy/letter.mat?dl=0',
    'http': 'https://www.dropbox.com/s/iy9ucsifal754tp/http.mat?dl=0',
}


def min_max_normalization(data):
    for i in range(data.shape[1]):
        min_x, max_x = np.min(data[:, i]), np.max(data[:, i])
        if min_x == max_x:
            data[:, i] = 0.5
        else:
            data[:, i] = (data[:, i] - min_x) / (max_x - min_x)
    return data


def read_data(dataset: str, normalize: bool = False):
    filename = f'../data/{dataset}/{dataset}.mat'
    if not os.path.exists(filename):
        run(['wget', DATASETS[dataset], '-O', f'../data/{dataset}/{dataset}.mat'])

    data_dict: Dict = {}
    try:
        import scipy.io
        data_dict = scipy.io.loadmat(filename)
    except NotImplementedError:
        import h5py
        with h5py.File(filename, 'r') as infile:
            for k, v in infile.items():
                if k in ['X', 'y']:
                    data_dict[k] = np.asarray(v, dtype=np.float64).T

    data = np.asarray(data_dict['X'], dtype=np.float64)
    labels = np.asarray(data_dict['y'], dtype=np.int8)

    if normalize is True:
        data = min_max_normalization(data)

    return data, labels


def make_umap(
        data: np.ndarray,
        n_neighbors: int,
        n_components: int,
        metric: str,
        filename: str,
) -> np.ndarray:
    if os.path.exists(filename):
        with open(filename, 'rb') as infile:
            embedding = pickle.load(infile)
    else:
        embedding = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            metric=metric,
        ).fit_transform(data)

        with open(filename, 'wb') as outfile:
            pickle.dump(embedding, outfile)

    return embedding


def plot_2d(
        data: np.ndarray,
        labels: np.ndarray,
        title: str,
        figsize=(8, 8),
        dpi=128,
):
    x, y = data[:, 0], data[:, 1]
    plt.close('all')
    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_subplot(111)
    ax.scatter(x, y, c=[float(d) for d in labels], s=10. * labels + 1., cmap='Dark2')
    plt.title(title)
    plt.show()
    plt.close('all')
    return


def plot_3d(
        dataset: str,
        metric: str,
        data: np.ndarray,
        labels: np.ndarray,
        title: str,
        folder: str,
        figsize=(8, 8),
        dpi=128,
):
    x, y, z = data[:, 0], data[:, 1], data[:, 2]
    plt.close('all')

    def _draw(azimuth):
        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c=[float(d) for d in labels], s=10. * labels + .1, cmap='Dark2')
        plt.title(title)
        plt.gca().set_axis_off()
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.margins(0, 0, 0)

        ax.view_init(elev=10, azim=azimuth)
        plt.savefig(folder + f'{azimuth:03d}.png', bbox_inches='tight', pad_inches=0)

    threads = [Thread(target=_draw, args=(azimuth,)) for azimuth in range(0, 360)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    plt.close('all')
    run([
        'ffmpeg', 
        '-framerate', '30', 
        '-i', f'{dataset}/frames/{metric}-%03d.png',
        '-c:v', 'libx264', 
        '-profile:v', 'high', 
        '-crf', '20', 
        '-pix_fmt', 'yuv420p', 
        f'{dataset}/{metric}-30fps.mp4'
    ])
    return


def make_dirs(datasets: List[str]):
    if not os.path.exists('../data'):
        os.mkdir('../data')

    for dataset in datasets:
        if not os.path.exists(f'../data/{dataset}'):
            os.mkdir(f'../data/{dataset}')
        for folder in ['umap', 'frames']:
            if not os.path.exists(f'../data/{dataset}/{folder}'):
                os.mkdir(f'../data/{dataset}/{folder}')

    # TODO: Figure out how to also download data here.
    return


def main():
    datasets = list(DATASETS.keys())
    make_dirs(datasets)

    metrics = [
        'euclidean',
        'manhattan',
        'cosine',
    ]

    for dataset in datasets:
        normalize = dataset not in ['mnist']
        data, labels = read_data(dataset, normalize)
        for metric in metrics:
            for n_neighbors in [32]:
                for n_components in [2, 3]:
                    filename = f'../data/{dataset}/umap/{n_neighbors}-{n_components}d-{metric}.pickle'
                    if data.shape[1] > n_components:
                        embedding = make_umap(data, n_neighbors, n_components, metric, filename)
                    else:
                        embedding = data
                    title = f'{dataset}-{metric}-{n_neighbors}'
                    if n_components == 3:
                        folder = f'../data/{dataset}/frames/{metric}-'
                        plot_3d(dataset, metric, embedding, labels, title, folder)
                        pass
                    if n_components == 2:
                        plot_2d(embedding, labels, title)
                        pass

    return


if __name__ == '__main__':
    main()