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
$ cd ./Metamong
$ ./setup.sh
```

## Reproduction

### 6.1 Effectiveness of Render-update Oracle
- To reproduce the result, please download and extract "6.1.zip" from [link](https://figshare.com/s/05656422846b31f368fc) and run the commands below.
- For Chrome bugs:
```shell
$ cd ./Metamong/src
$ python3 repro.py [path/to/6.1/chrome]  # to reproduce the result of Chrome

Oracle detects the bug, poc: ../testenv/6.1/chrome/1163031/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1167352/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1188753/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1189195r/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1190987/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1205650/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1206914/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1222734/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1283279/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1285883r/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1291930/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1305109/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1311813/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1373252/poc.html
Oracle detects the bug, poc: ../testenv/6.1/chrome/1402075/poc.html
bug: 15, num: 15
```

- For Firefox bugs:
```shell
$ cd ./Metamong/src
$ python3 repro.py [path/to/6.1/firefox] # to reproduce the result of Firefox 
```

### 6.2 Effectiveness of Page Mutator
- To reproduce the result, please download and extract "6.2.zip" from [link](https://figshare.com/s/05656422846b31f368fc) and run the commands below.

```shell
$ cd ./Metamong/src
$ ./internal_eval_script.sh chrome [path/to/6.2/100k_inputs] # Test Chrome
$ ./internal_eval_script.sh firefox [path/to/6.2/100k_inputs] # Test Firefox
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
