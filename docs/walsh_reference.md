# Adapted Walsh CNN reference

This separate full-spectrum reference follows the architecture and optimization
constants in the [authors' `build_cnn` implementation](https://github.com/jemjemwalsh/research-deep-learning-nirs/blob/0d939025cf30df1cfaf6afdc35c7de34de0b03b1/publications/Eval-1D-CNN-Mango-DM/utils/models.py)
for Walsh, Neupane and Li (2024), DOI 10.1016/j.saa.2024.124003.
The verified source commit is `0d939025cf30df1cfaf6afdc35c7de34de0b03b1`;
`utils/models.py` SHA-256 is
`f1ae16dcd04440f22e74f293f8af7a3d592c7672e5b1ae37194beb2fad3f753c`.
The author thesis chapter 3 was also inspected; see the literature audit.

The network has one 21-position convolutional filter with same-length padding,
ELU activation, flattening, dense layers of 36, 18 and 12 ELU units, and a scalar
linear output. All kernel matrices use He-normal initialization and an explicit
L2 loss coefficient of 0.0055; biases are initialized to zero and unpenalized.
Adam starts at 0.005 with batch size 128 and a maximum of 750 epochs. Validation
loss includes kernel regularization, as in Keras. A plateau scheduler reduces the
learning rate by 0.5 after 25 unimproved epochs, with a floor of 1e-6. Early
stopping waits 50 epochs with minimum loss improvement 1e-5 and restores the best
state. The scheduler's minimum improvement is the Keras default 1e-4.

This is an **adaptation**, not an exact reproduction or a claim of matching the
published score. It uses this study's 103 raw absorbance inputs, training-subset
column standardization, and unscaled targets. It does not recreate the authors'
six concatenated preprocessing variants, their 618-feature model, or their split.
PyTorch He-normal initialization is untruncated, unlike Keras HeNormal; random
streams and optimizer implementations differ. Twenty percent of supplied fitting
groups (seed 42) are reserved for early stopping and scaling is fitted only on
the remaining groups. The outer calibration partition is not used. This sacrifices
some fitting observations to maintain a separate stopping subset. No refit after
choosing epochs uses that stopping subset. The reference is evaluated once with
seed 42 on each development held season and on the frozen external seasons.

`mango.walsh_reference.fit_walsh(X, y, groups, seed=42)` returns a serializable
model with `predict(X)` and a `fit_info` dictionary containing the split, full
training history, best epoch and source identifiers. Its optional `max_epochs`
argument is for software smoke checks; registered fits use 750.

The existing compact two-convolution network is a generic secondary CNN. Its
architecture does not match the author network and it should not be presented as
the Walsh reference. Neither CNN reference establishes the true information
content of the full spectrum: reference choice remains a modeling sensitivity.
