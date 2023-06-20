# Metamong

An automatic tool that finds render-update bugs in the browser.

## Table                                                                                     
1. [Setup](#Setup)    
2. [Tutorial](#Tutorial)                                                                                                       

## Setup
- You need to install the dependencies of Metamong.
- The bash file `setup.sh` will install all of the dependencies.

```shell
$ cd Metamong
$ ./setup.sh
```

## Tutorial
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
