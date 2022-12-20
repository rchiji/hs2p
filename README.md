<h1 align="center">Histopathology Slide Pre-processing Pipeline</h2>


HS2P is an open-source project largely based on [CLAM](https://github.com/mahmoodlab/CLAM) tissue segmentation and patching code. 

<p>
   <a href="https://github.com/psf/black"><img alt="empty" src=https://img.shields.io/badge/code%20style-black-000000.svg></a>
   <a href="https://github.com/PyCQA/pylint"><img alt="empty" src=https://img.shields.io/github/stars/clemsgrs/hs2p?style=social></a>
</p>

<img src="illustration.png" width="1000px" align="center" />

## Requirements

install requirements via `pip3 install -r requirements.txt`

## Step-by-step guide

1. [Optional] Configure wandb

If you want to benefit from wandb logging, you need to follow these simple steps:
 - grab your wandb API key under your profile and export
 - run the following command in your terminal: `export WANDB_API_KEY=<your_personal_key>`
 - change wandb paramters in the config file under `config/` (mainly `project` and `username`)

2. Create a new folder under the `data/` directory and give that folder a name.<br>
Then, place your slides in the `slides` folder under that new folder:

```
hs2p/ 
├── source/
├── config/
├── data/
│     └── <dataset_name>/
│          └── slides/
│             ├── slide_1.tif
│             ├── slide_2.tif
│             └── ...
```

3. Create a configuration file under `config` and change parameters as you wish.<br>
A good starting point is to use the default configuration file `config/default.yaml` where parameters are documented.

4. Run the following command to kick off the algorithm:

`python3 main.py --config-name <config_filename>`

5. Depending on which flags have been set to True, it will produce (part of) the following results:


```
hs2p/ 
├── output/<dataset_name>/<experiment_name>/
│     ├── masks/
│     │     ├── slide_1.jpg
│     │     ├── slide_2.jpg
│     │     └── ...
│     ├── patches/
│     │        ├── slide_1/
│     │        │   └── <patch_size>/
│     │        │       ├── slide_1.h5
│     │        │       └── jpg/
│     │        │          ├── x0_y0.jpg
│     │        │          ├── x1_y0.jpg
│     │        │          └── ...
│     │        ├── slide_2/
│     │        └── ...
│     ├── stitches/
│     │     ├── slide_1_<patch_size>.jpg
│     │     ├── slide_2_<patch_size>.jpg
│     │     └── ...
│     └── process_list.csv
```

## Resuming experiment after crash / bug

If, for some reason, the experiment crashes, you should be able to resume from last processed slide simply by turning the `resume` parameter in your config file to `True`, keeping all other parameters unchanged.

## TODO List

- [ ] improve documentation
- [ ] make patch saving to disk faster (using multiprocessing?)
- [ ] add support for deep-learning based tissue segmentation
- [ ] add support for black patch removal in latest contour processing function
