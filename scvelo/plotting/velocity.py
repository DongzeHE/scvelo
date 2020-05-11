from .. import settings
from ..preprocessing.moments import second_order_moments
from ..tools.rank_velocity_genes import rank_velocity_genes
from .scatter import scatter
from .utils import savefig_or_show, default_basis, default_size, get_basis, get_figure_params

import numpy as np
import pandas as pd
import matplotlib.pyplot as pl
from matplotlib import rcParams
from scipy.sparse import issparse


def velocity(adata, var_names=None, basis=None, vkey='velocity', mode=None, fits=['velocity', 'dynamics'], layers='all',
             color=None, color_map=['RdYlGn', 'gnuplot_r'], colorbar=True, perc=[2,98], alpha=.5, size=None, groupby=None,
             groups=None, legend_loc='none', legend_fontsize=8, use_raw=False, fontsize=None, figsize=None, dpi=None,
             show=True, save=None, ax=None, ncols=None, **kwargs):
    """Phase and velocity plot for set of genes.

    The phase plot shows spliced against unspliced expressions with steady-state fit.
    Further the embedding is shown colored by velocity and expression.

    Arguments
    ---------
    adata: :class:`~anndata.AnnData`
        Annotated data matrix.
    var_names: `str` or list of `str` (default: `None`)
        Which variables to show.
    basis: `str` (default: `'umap'`)
        Key for embedding coordinates.
    mode: `'stochastic'` or `None` (default: `None`)
        Whether to show show covariability phase portrait.
    fits: `str` or list of `str` (default: `'all'`)
        Which steady-state estimates to show.
    layers: `str` or list of `str` (default: `'all'`)
        Which layers to show.
    color: `str`,  list of `str` or `None` (default: `None`)
        Key for annotations of observations/cells or variables/genes
    color_map: `str` or tuple (default: `matplotlib.rcParams['image.cmap']`)
        String denoting matplotlib color map.
        If tuple is given, first and latter color map correspond to velocity and expression, respectively.
    perc: tuple, e.g. [2,98] (default: `None`)
        Specify percentile for continuous coloring.
    groups: `str`, `list` (default: `None`)
        Subset of groups, e.g. [‘g1’, ‘g2’, ‘g3’], to which the plot shall be restricted.
    groupby: `str`, `list` or `np.ndarray` (default: `None`)
        Key of observations grouping to consider.
    legend_loc: str (default: 'none')
        Location of legend, either 'on data', 'right margin' or valid keywords for matplotlib.legend.
    size: `float` (default: 5)
        Point size.
    alpha: `float` (default: 1)
        Set blending - 0 transparent to 1 opaque.
    fontsize: `float` (default: `None`)
        Label font size.
    figsize: tuple (default: `(7,5)`)
        Figure size.
    dpi: `int` (default: 80)
        Figure dpi.
    show: `bool`, optional (default: `None`)
        Show the plot, do not return axis.
    save: `bool` or `str`, optional (default: `None`)
        If `True` or a `str`, save the figure. A string is appended to the default filename.
        Infer the filetype if ending on {'.pdf', '.png', '.svg'}.
    ax: `matplotlib.Axes`, optional (default: `None`)
        A matplotlib axes object. Only works if plotting a single component.
    ncols: `int` or `None` (default: `None`)
        Number of columns to arange multiplots into.

    """
    basis = default_basis(adata) if basis is None else get_basis(adata, basis)
    color, color_map = kwargs.pop('c', color), kwargs.pop('cmap', color_map)

    if isinstance(groupby, str) and groupby in adata.obs.keys():
        if 'rank_velocity_genes' not in adata.uns.keys() or adata.uns['rank_velocity_genes']['params']['groupby'] != groupby:
            rank_velocity_genes(adata, vkey=vkey, n_genes=10, groupby=groupby)
        names = np.array(adata.uns['rank_velocity_genes']['names'].tolist())
        if groups is None:
            var_names = names[:, 0]
        else:
            groups = [groups] if isinstance(groups, str) else groups
            idx = np.array([any([g in group for g in groups]) for group in adata.obs[groupby].cat.categories])
            var_names = np.hstack(names[idx, :int(10 / idx.sum())])
    elif var_names is not None:
        var_names = [var_names] if isinstance(var_names, str) else [var for var in var_names if var in adata.var_names]
    else:
        raise ValueError('No var_names or groups specified.')
    var_names = pd.unique(var_names)

    (skey, ukey) = ('spliced', 'unspliced') if use_raw or 'Ms' not in adata.layers.keys() else ('Ms', 'Mu')
    layers = [vkey, skey] if layers == 'all' else layers
    layers = [layer for layer in layers if layer in adata.layers.keys() or layer == 'X']

    fits = list(adata.layers.keys()) if fits == 'all' else fits
    fits = [fit for fit in fits if fit == 'dynamics' or fit + '_gamma' in adata.var.keys()] + ['dynamics']
    stochastic_fits = [fit for fit in fits if 'variance_' + fit in adata.layers.keys()]

    nplts = (1 + len(layers) + (mode == 'stochastic') * 2)
    ncols = 1 if ncols is None else ncols
    nrows = int(np.ceil(len(var_names) / ncols))
    ncols = int(ncols * nplts)
    figsize = rcParams['figure.figsize'] if figsize is None else figsize
    figsize, dpi = get_figure_params(figsize, dpi, ncols / 2)
    ax = pl.figure(figsize=(figsize[0] * ncols / 2, figsize[1] * nrows / 2), dpi=dpi) if ax is None else ax
    gs = pl.GridSpec(nrows, ncols, wspace=.5, hspace=.8)

    size = default_size(adata) / 2 if size is None else size  # since fontsize is halved in width and height
    fontsize = rcParams['font.size'] * .8 if fontsize is None else fontsize

    for v, var in enumerate(var_names):
        _adata = adata[:, var]
        s, u = _adata.layers[skey], _adata.layers[ukey]
        if issparse(s): s, u = s.A, u.A

        # spliced/unspliced phase portrait with steady-state estimate
        ax = pl.subplot(gs[v * nplts])
        cmap = color_map
        if isinstance(color_map, (list, tuple)):
            cmap = color_map[-1] if color in ['X', skey] else color_map[0]
        if 'xlabel' not in kwargs: kwargs['xlabel'] = 'spliced'
        if 'ylabel' not in kwargs: kwargs['ylabel'] = 'unspliced'
        scatter(adata, basis=var, color=color, colorbar=colorbar, color_map=cmap, perc=perc, frameon=True, title=var,
                size=size, use_raw=use_raw, alpha=alpha, fontsize=fontsize, vkey=fits, legend_fontsize=legend_fontsize,
                show=False, ax=ax, save=False, legend_loc_lines='none' if v < len(var_names)-1 else legend_loc, **kwargs)

        # velocity and expression plots
        for l, layer in enumerate(layers):
            ax = pl.subplot(gs[v * nplts + l + 1])
            title = 'expression' if layer in ['X', skey] else layer
            #_kwargs = {} if title == 'expression' else kwargs
            cmap = color_map
            if isinstance(color_map, (list, tuple)):
                cmap = color_map[-1] if layer in ['X', skey] else color_map[0]
            scatter(adata, basis=basis, color=var, layer=layer, colorbar=colorbar, title=title, perc=perc,
                    color_map=cmap, use_raw=use_raw, fontsize=fontsize, size=size, alpha=alpha, frameon=False,
                    show=False, ax=ax, save=False, **kwargs)

        if mode == 'stochastic':
            ss, us = second_order_moments(_adata)
            s, u, ss, us = s.flatten(), u.flatten(), ss.flatten(), us.flatten()
            fit = stochastic_fits[0]

            ax = pl.subplot(gs[v * nplts + len(layers) + 1])
            offset = _adata.var[fit + '_offset'] if fit + '_offset' in adata.var.keys() else 0
            beta = _adata.var[fit + '_beta'] if fit + '_beta' in adata.var.keys() else 1
            x = np.array(2 * (ss - s**2) - s)
            y = np.array(2 * (us - u * s) + u + 2 * s * offset / beta)
            kwargs['xlabel'] = r'2 $\Sigma_s - \langle s \rangle$'
            kwargs['ylabel'] = r'2 $\Sigma_{us} + \langle u \rangle$'
            scatter(adata, x=x, y=y, color=color, colorbar=colorbar, title=var, fontsize=fontsize, size=size, perc=perc,
                    use_raw=use_raw, frameon=True, ax=ax, save=False, show=False, **kwargs)

            xnew = np.linspace(np.min(x), np.max(x) * 1.02)
            for fit in stochastic_fits:
                gamma = _adata.var[fit + '_gamma'].values if fit + '_gamma' in adata.var.keys() else 1
                beta = _adata.var[fit + '_beta'].values if fit + '_beta' in adata.var.keys() else 1
                offset2 = _adata.var[fit + '_offset2'].values if fit + '_offset2' in adata.var.keys() else 0

                pl.plot(xnew, gamma / beta * xnew + offset2 / beta, c='k', linestyle='--')

    savefig_or_show(dpi=dpi, save=save, show=show)
    if not show: return ax
