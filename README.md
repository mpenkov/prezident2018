# prezident2018

Collecting and analyzing results of the 2018 Russian presidential election.

A copy of the most recently collected results is in scrapyproject/results.json.gz

## Scraping

You'll need the required packages first:

    pip install -r requirements.txt

To scrape the results, run:

    cd scrapyproject
    scrapy runspider -t lines prezident2018/spiders/myspider.py -o results.json

## Testing

    py.test scrapyproject

## Analyzing

See the following Jupyter notebooks:

- Introduction.ipynb: describes the data set and shows some examples of working with it
- Graphs.ipynb: some graphing examples
- Turnout.ipynb: analyzing the election turnout
