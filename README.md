# Metamong: Detecting Render-Update Bugs in Web Browsers through Fuzzing

An automatic tool that finds render-update bugs in the browser.

## Table                                                                                     
1. [Setup](#Setup)
2. [Reproduction](#Reproduction)
3. [Usage](#Usage)
4. [Environment](#Environment)

## Setup
- You need to download the source code of Metamong and install its dependencies.
- Source code and all dataset used in paper is published at this [link](https://figshare.com/s/05656422846b31f368fc).
- Please download and extract them if you want to reproduce the result of paper.
- After extracting the "source code.zip", run the bash file `setup.sh` to install all of the dependencies.

```shell
$ ./setup.sh
```

## Reproduction

### 6.1 Effectiveness of Render-update Oracle
- To reproduce the result, please run the commands below.
```shell
$ cd ./src/
```

### 6.2 Effectiveness of Page Mutator
- To reproduce the result, please run the commands below.
```shell
$ TODO
```

## Usage
- First, you need to generate the html files.

```shell
$ cd Metamong/src/domato
$ python3 generator.py --output_dir ./html_testcases --no_of_files 10000
```
* This will generate 10,000 testcases in `./html_testcases` directory. 
* Now you can run Metamong with `metamong.py`.
* It provides six options:
  * -t: The type of browser (e.g., chrome)
  * -i: The html testcase directory
  * -o: The output directory
  * -j: The number of threads
  * -p: The previous version of browser
  * -n: The newer version of browser

```shell
$ cd Metamong/src/
$ python3 metamong.py -i ./domato/html_testcases -o ./outputs -j 24 -p 102 -n 104 -t chrome
```

## Environment
- OS: Ubuntu 20.04 64bit
- CPU: x86-64
- Memory: larger than 64GB RAM
- Storage: larger than 64GB
- Softwares :Python3, Selenium Library, Chrome, Firefox
