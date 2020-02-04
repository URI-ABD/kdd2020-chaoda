import logging
import random
import os
from glob import glob

import click
import numpy as np
from sklearn.metrics import roc_auc_score

from chess.manifold import Manifold
from chess import criterion

from .datasets import DATASETS, DATA_DIR, get, read
from .methods import METHODS, normalize
from .plot import RESULT_PLOTS, plot_2d, plot_3d

np.random.seed(42)
random.seed(42)

METRICS = {
    'cosine': 'cosine',
    'euclidean': 'euclidean',
    'manhattan': 'cityblock',
}

BUILD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'build'))


def _manifold_path(dataset, metric, min_points, graph_ratio) -> str:
    """ Generate proper path to manifold. """
    return os.path.join(
        BUILD_DIR,
        ':'.join(map(str, [dataset, metric, min_points, f'{graph_ratio}.pickle']))
    )


def _dataset_from_path(path):
    return os.path.basename(path).split(':')[0]


def _metric_from_path(path):
    return os.path.basename(path).split(':')[1]


def _meta_from_path(path):
    bundle = os.path.basename(path).split(':')
    return {
        'dataset': bundle[0],
        'metric': bundle[1],
        'min_points': bundle[2],
        'graph_ratio': bundle[3].split('.pickle')[0],
    }


@click.group(chain=True)
def cli():
    pass


@cli.command()
@click.option('--dataset', type=click.Choice(DATASETS.keys()))
@click.option('--metric', type=click.Choice(DATASETS.keys()))
@click.option('--max-depth', type=int, default=100)
@click.option('--graph-ratio', type=int, default=98)
def build(dataset, metric, max_depth, graph_ratio):
    datasets = [dataset] if dataset else DATASETS.keys()
    metrics = [metric] if metric else METRICS.keys()
    
    for dataset in datasets:
        get(dataset)
        data, labels = read(dataset)

        for metric in metrics:
            logging.info('; '.join([
                f'dataset: {dataset}',
                f'metric: {metric}',
                f'shape: {data.shape}',
                f'outliers: {len(np.where(labels > 0.9)[0]) / len(labels)}'
            ]))
            manifold = Manifold(data, METRICS[metric])

            min_points = 5 if data.shape[0] > 50_000 else 1            
            manifold.build(
                criterion.MaxDepth(max_depth),
                criterion.MinPoints(min_points),
            )
            filepath = _manifold_path(dataset, metric, min_points, graph_ratio)
            with open(filepath, 'wb') as fp:
                logging.info(f'dumping manifold {filepath}')
                manifold.dump(fp)


@cli.command()
@click.option('--method', type=click.Choice(METHODS.keys()))
@click.option('--dataset', type=str, default='*')
@click.option('--metric', type=str, default='*')
@click.option('--min-points', type=str, default='*')
@click.option('--graph-ratio', type=str, default='*')
def test(method, dataset, metric, min_points, graph_ratio):
    methods = [method] if method else METHODS.keys()
    for path in glob(_manifold_path(dataset, metric, min_points, graph_ratio)):
        data, labels = read(_dataset_from_path(path))
        
        # Load the manifold.
        with open(path, 'rb') as fp:
            manifold = Manifold.load(fp, data)

        for method in methods:
            for depth in range(0, manifold.depth + 1, 1):
                # These methods are invariant to depth.
                if method in {'n_points_in_ball', 'k_nearest'} and depth < manifold.depth:
                    continue
                logging.debug(f'calling {method} with {manifold}')
                anomalies = METHODS[method](manifold.graphs[depth])
                try:
                    logging.info('; '.join([
                        f'depth: {depth:>3}',
                        f'subgraphs: {len(manifold.graphs[depth].subgraphs):>5}',
                        f'clusters: {len(manifold.graphs[depth].clusters.keys()):>5}',
                        f'AUC Score: {roc_auc_score(labels, list(anomalies.values())):03.2f}',
                        f'{method}'
                    ]))
                except Exception as e:
                    logging.exception(e)


@cli.command()
@click.option('--plot', type=click.Choice(RESULT_PLOTS.keys()))
@click.option('--method', type=click.Choice(METHODS.keys()))
@click.option('--dataset', type=str, default='*')
@click.option('--metric', type=str, default='*')
@click.option('--min-points', type=str, default='*')
@click.option('--graph-ratio', type=str, default='*')
def plot_results(plot, method, dataset, metric, min_points, graph_ratio):
    methods = [method] if method else METHODS.keys()
    plots = [plot] if plot else RESULT_PLOTS.keys()
    for manifold in glob(_manifold_path(dataset, metric, min_points, graph_ratio)):
        meta = _meta_from_path(manifold)
        dataset = meta['dataset']
        metric = meta['metric']
        data, labels = read(dataset)
        with open(manifold, 'rb') as fp:
            manifold = Manifold.load(fp, data)
        for method in methods:
            for depth in range(0, manifold.depth + 1):
                if method in {'n_points_in_ball', 'k_nearest'} and depth < manifold.depth:
                    continue
                for plot in plots:
                    logging.info(f'{dataset}, {depth}, {plot}')
                    RESULT_PLOTS[plot](
                        labels, 
                        METHODS[method](manifold.graphs[depth]),
                        dataset,
                        metric,
                        method,
                        depth,
                        save=True
                    )


@cli.command()
def plot_data():
    # TODO
    raise NotImplementedError
    for dataset in datasets: 
        normalize = dataset not in ['mnist']
        data, labels = read(dataset, normalize)
        min_points = 5 if data.shape[0] > 50_000 else 1            
        for metric in metrics:
            # TODO
            for n_neighbors in [32]:
                for n_components in [3]:
                    filename = os.path.join(BUILD_DIR, dataset)
                    filename = f'../data/{dataset}/umap/{n_neighbors}-{n_components}d-{metric}.pickle'
                    if data.shape[1] > n_components:
                        embedding = data
                        # embedding = make_umap(data, n_neighbors, n_components, metric, filename)
                    else:
                        embedding = data
                    title = f'{dataset}-{metric}-{n_neighbors}'
                    if n_components == 3:
                        # folder = f'../data/{dataset}/frames/{metric}-'
                        # plot_3d(embedding, labels, title, folder)


                        pass
                    if n_components == 2:
                        # plot_2d(embedding, labels, title)
                        pass


@cli.command()
@click.option('--dataset', type=str, default='*')
@click.option('--metric', type=str, default='*')
def animate(dataset, metric):
    # TODO
    raise NotImplementedError
    run([
        'ffmpeg',
        '-framerate', '30',
        '-i', os.path.join(dataset, 'frames', f'{metric}-%03d.png'),
        '-c:v', 'libx264',
        '-profile:v', 'high',
        '-crf', '20',
        '-pix_fmt', 'yuv420p',
        os.path.join(dataset, f'{metric}-30fps.mp4'),
    ])


if __name__ == "__main__":
    os.makedirs(BUILD_DIR, exist_ok=True)
    cli(prog_name='src')
