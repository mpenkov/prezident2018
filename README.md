Collecting and analyzing results of the 2018 Russian presidential election.

To scrape the results, run:

    cd scrapyproject
    scrapy runspider -t lines prezident2018/spiders/myspider.py -o results.json

A copy of the most recently collected results is in scrapyproject/results.json.gz
