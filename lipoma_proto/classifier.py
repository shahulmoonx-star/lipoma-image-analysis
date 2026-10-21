"""Training helpers: logistic-regression heads on frozen BiomedCLIP features (optionally fused with a
zero-shot text prior)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from . import config

_FLOOR = 1e-4      # probability given by the image classifier to a class it never saw in training


def l2(a: np.ndarray) -> np.ndarray:
    a = np.atleast_2d(a)
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)


@dataclass
class TextPrior:
    """BiomedCLIP zero-shot match between an image and the name of every class."""
    classes: np.ndarray          # all class names
    emb: np.ndarray              # [n_classes, d] L2-normalised text embeddings
    weight: float = config.TEXT_PRIOR_WEIGHT
    temp: float = config.TEXT_PRIOR_TEMP

    def log_proba(self, X: np.ndarray) -> np.ndarray:
        z = self.temp * (l2(X) @ self.emb.T)
        z = z - z.max(1, keepdims=True)
        return z - np.log(np.exp(z).sum(1, keepdims=True))


@dataclass
class Head:
    scaler: StandardScaler
    clf: LogisticRegression
    prior: TextPrior | None = None

    @property
    def classes(self) -> np.ndarray:
        return self.prior.classes if self.prior is not None else self.clf.classes_

    def proba(self, X: np.ndarray) -> np.ndarray:
        p = self.clf.predict_proba(self.scaler.transform(l2(X)))
        if self.prior is None:
            return p
        col = {c: i for i, c in enumerate(self.prior.classes)}
        lp = np.full((len(p), len(self.prior.classes)), np.log(_FLOOR))
        for j, c in enumerate(self.clf.classes_):
            lp[:, col[c]] = np.log(p[:, j] + 1e-9)
        s = lp + self.prior.weight * self.prior.log_proba(X)
        s = np.exp(s - s.max(1, keepdims=True))
        return s / s.sum(1, keepdims=True)


def fit_head(X: np.ndarray, y: np.ndarray, C: float = config.LOGREG_C, prior: TextPrior | None = None) -> Head:
    a = l2(X)
    scaler = StandardScaler().fit(a)
    clf = LogisticRegression(C=C, max_iter=3000, class_weight="balanced")
    clf.fit(scaler.transform(a), y)
    return Head(scaler, clf, prior)


def cross_val_proba(X: np.ndarray, y: np.ndarray, groups: np.ndarray, repeats: int = 5,
                    n_splits: int = 5, C: float = config.LOGREG_C, prior: TextPrior | None = None):
    """Out-of-fold class probabilities (mean over `repeats` shuffled grouped K-folds).

    Images that are copies of each other share a group, so a picture and its copy are never
    split between training and test data.

    Returns (classes, proba[n, n_classes] averaged over repeats, per-repeat list of predictions)."""
    classes = np.unique(y)
    index = {c: i for i, c in enumerate(classes)}
    acc = np.zeros((len(y), len(classes)))
    per_repeat = []
    for seed in range(repeats):
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        pred = np.empty(len(y), dtype=object)
        P_rep = np.zeros_like(acc)
        for tr, te in cv.split(X, y, groups):
            head = fit_head(X[tr], y[tr], C, prior)
            p = head.proba(X[te])
            for j, c in enumerate(head.classes):
                P_rep[te, index[c]] = p[:, j]
        pred[:] = classes[P_rep.argmax(1)]
        per_repeat.append((pred, P_rep.copy()))
        acc += P_rep
    return classes, acc / repeats, per_repeat


def topk_hits(classes: np.ndarray, P: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    order = np.argsort(-P, axis=1)[:, :k]
    return np.array([y[i] in classes[order[i]] for i in range(len(y))])


def max_similarity_outside_group(Xn: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """For each image: highest cosine similarity to any image of a *different* group."""
    sim = Xn @ Xn.T
    same = groups[:, None] == groups[None, :]
    sim[same] = -1.0
    return sim.max(axis=1)
