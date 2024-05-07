from setuptools import setup, find_packages

setup(
    name='interview_transcriber',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'pytube',
        'tqdm',
        'pydub',
        'openai==1.17.0',
        'pytest',
        'pyannote.audio',
        'webvtt-py',
        'umap-learn',
        'git+https://github.com/NVIDIA/NeMo.git@main#egg=nemo_toolkit[asr]'
    ],
)