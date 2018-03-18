#
# Landing pages
#
wget -O central_ik_home.html "http://www.vybory.izbirkom.ru/region/izbirkom?action=show&root_a=12000009&vrn=100100084849062&region=0&global=true&type=0&prver=0&pronetvd=null"
wget -O cb_region_ik_home.html "http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=1000001&tvd=100100084849067&vrn=100100084849062&prver=0&pronetvd=null&region=0&sub_region=0&type=0&vibid=100100084849067"

#
# Turnout results.
#
wget -O regional_ik_turnout.html "http://www.vybory.izbirkom.ru/region/region/izbirkom?action=show&root=1000063&tvd=100100084849189&vrn=100100084849062&region=0&global=true&sub_region=0&prver=0&pronetvd=null&vibid=100100084849189&type=453"
wget -O territorial_ik_turnout.html "http://www.sakhalin.vybory.izbirkom.ru/region/region/sakhalin?action=show&tvd=100100084849189&vrn=100100084849062&region=65&global=true&sub_region=65&prver=0&pronetvd=null&type=453&vibid=2652000451223"
wget -O territorial_ik_intermediate.html "http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=652000016&tvd=2652000451223&vrn=100100084849062&prver=0&pronetvd=null&region=0&sub_region=0&type=453&vibid=2652000451223"
wget -O territorial_ik_uik_turnout.html "http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=652000016&tvd=2652000451223&vrn=100100084849062&prver=0&pronetvd=null&region=65&sub_region=65&type=453&vibid=2652000451223"
