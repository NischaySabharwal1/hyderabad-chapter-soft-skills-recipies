from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from numpy import str_ 
import requests
import re
import time
from datetime import datetime
from tqdm import tqdm
import pandas as pd
import numpy as np
import itertools
from tabulate import tabulate
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class SearchOptions():

  apikey = '***'
  cse_id = '***'

  def get_soup(self,data, parser = 'html.parser'):
    return BeautifulSoup(data, parser)

  def selenium_driver(self):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--incognito')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1200')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options = chrome_options)
    return driver

  def return_lists(self, criterias, skills, forums):
    skills = np.asarray([skills]).flatten()
    criterias = np.asarray([criterias]).flatten()
    forums = np.asarray([forums]).flatten()
    return skills, criterias, forums

  def get_search_bar_results(self, criterias, skills, urls=' ', n:int=12)->pd.DataFrame:
    skills,criterias,urls = self.return_lists(criterias, skills, urls)
    def form_url(url, q):
      q = q.replace(' ', '+')
      if url == ' ':
        surl = f"https://www.google.com/search?q={q}"
      else: 
        surl = f"https://www.google.com/search?q=site%3A{url}+{q}"
      return surl

    def search_results(criteria: str, skill: str, url: str='', n: int=10)->pd.DataFrame:

        driver = self.selenium_driver()
        query = criteria+ ' ' +skill
        burl = 'https://www.google.com'

        searchurl = form_url(url,query)
          
        art_links = {x:[] for x in ['Skill', 'Criteria', 'Title', 'Link', 'Content']}
        df = pd.DataFrame(art_links)
        results = []
        while True:
            
          driver.get(searchurl)
          soup = self.get_soup(driver.page_source)
          try:
            results = soup.select_one('div.GyAeWb div.v7W49e').find_all('div', class_='MjjYud')
            print(len(results))
          except Exception: break
          c=0
          for ele in results:
            try:
              link = ele.select_one('div.yuRUbf a').get('href')
              title = ele.select_one('div.yuRUbf').a.select_one('h3').text
            #snip = driver.find_element(By.XPATH, "/html/body/div[7]/div/div[11]/div/div[2]/div[2]/div/div/div[1]/div/div/div[2]/div").get_attribute('innerHTML')
            #snippet = BeautifulSoup(snip).text
              d = re.sub(r'\.\w+\/\*?', '', re.search(r'\w+\.\w*\/', link).group())
              art_links['Skill'].append(skill)
              art_links['Criteria'].append(query)
              art_links['Title'].append(title)
              art_links['Link'].append(link)
              art_links['Content'].append('')
            #art_links['snippet'].append(snippet)
              c+=1
              n-=1
            except Exception: 
              continue
            if c>=10 or n==0:
              break
          try: 

            element = driver.find_element(By.XPATH, "/html/body/div[7]/div/div[11]/div/div[4]/div/div[2]/table/tbody/tr").get_attribute('innerHTML')
            next_page = burl + self.get_soup(element).find_all('td')[-1].a.get('href')

          except Exception: next_page = None

          df = pd.concat([df,pd.DataFrame(art_links)], ignore_index=True).drop_duplicates()  

          if n<=0 or next_page==None:
            driver.close()
            return df
          else: 
            searchurl = next_page
            time.sleep(2)
        
        return df

    
    combinations = list(itertools.product(criterias,skills,urls))
    df_links = pd.DataFrame({})
    for combn in combinations:
      df_links = pd.concat([df_links, search_results(combn[0], combn[1], combn[2], n)], ignore_index=True)
    return df_links

  def get_api_results(self, criterias, skills, urls=' ', n:int = 12):
    skills,criterias,urls = self.return_lists(criterias, skills, urls)
    def api_query_results(criteria: str, skill: str, url: str='', n: int=10)->pd.DataFrame:
        resource = build("customsearch", "v1", developerKey=self.apikey).cse()
        art_links = {x:[] for x in ['Skill', 'Criteria', 'Title', 'Link', 'Content']}
        query = criteria +' '+ skill
        if url != '':
            query = f"site:{url} {query}"
        
        results = []
        for i in range(1, n, 10):
            try:
                results += resource.list(q=query, cx = self.cse_id, start = i).execute()['items']
            except KeyError: 
              print('No results returned')
              return pd.DataFrame(art_links)
        
        
            for r in results:
                
                art_links['Skill'].append(skill)
                art_links['Title'].append(r['title'])
                art_links['Link'].append(r['link'])
                art_links['Criteria'].append(criteria)
                #d = re.sub(r'\.\w+\/\*?', '', re.search(r'\w+\.\w*\/', r['link']).group())
                art_links['Content'].append('')
                
        df = pd.DataFrame(art_links).drop_duplicates(ignore_index=True)
        
        return df
    combinations = list(itertools.product(criterias,skills,urls))
    df_links = pd.DataFrame({})
    for combn in combinations:
      df_links = pd.concat([df_links, api_query_results(combn[0], combn[1], combn[2], n)], ignore_index=True)
    return df_links

  def forum_search(self, criterias, skills, forums, n:int=10):
    driver = self.selenium_driver()
    skills,criterias,forums = self.return_lists(skills, criterias, forums)
    df = pd.DataFrame({})
    def medium(criteria:str, skill:str, n:int=10)->pd.DataFrame:
        
        def pagination(driver, n):
            n /= 10
            while n>0:
                try:
                    #Finding and clicking the show more button on the webpage for more articles, till it exists
                    elm = driver.find_element(By.CSS_SELECTOR, 'button.co')
                    elm.click()
                    n-=1
                    time.sleep(0.5)
                except Exception:
                    break
        
        burl = "https://medium.com"
        url = "https://medium.com/search/posts?q=" + criteria.replace(' ', '+') + '+' +  skill.replace(' ', '+')
        art_links = {x:[] for x in ['Skill', 'Criteria', 'Title', 'Link', 'Content']}
        driver.get(url) #open the webpage in the browser based on criteria
        pagination(driver,n) #click show more button multiple times
        #Find the tag section under which all the article links are present, by using XPATH
        ele = driver.find_element(By.XPATH, '/html/body/div/div/div[3]/div/div/main/div/div/div[2]').get_attribute('outerHTML')
        soup = self.get_soup(ele)
        #Store html content of each article link in a list called arts
        arts = soup.find_all('div', class_='ce l')
        for art in arts:
            try:
                c = art.find('a', {'aria-label':'Post Preview Title'}) #grab article section html
                link = burl+ c.get('href') #grab article link
                title = c.find('h2').text.strip() #extract article title
                art_links['Skill'].append(skill)
                art_links['Criteria'].append(criteria)
                art_links['Content'].append('') #content is maintained empty for scraping content to be stored in the same df for convenience
                if link not in art_links['Link']:
                    art_links['Link'].append(link)
                    art_links['Title'].append(title)
            except AttributeError:
                continue
        df = pd.DataFrame(art_links).drop_duplicates(ignore_index=True)
        return df
    
    def wikihow(criteria:str, skill:str, n:int=10)->pd.DataFrame:
        art_links = {x:[] for x in ['Skill', 'Criteria', 'Title', 'Link', 'Content']}
        url = "https://www.wikihow.com/wikiHowTo?search=" + criteria.replace(' ', '+') + '+' +  skill.replace(' ', '+')
        n1=n
        driver.get(url) 
        while n1>0:
            ele = driver.find_element(By.XPATH, '/html/body/div[4]/div[2]/div[2]/div[1]/div/div[1]/div[2]').get_attribute('outerHTML')
            soup = self.get_soup(ele)
            arts = soup.find_all('a', class_='result_link')
            art_links['Link'] += [x.get('href') for x in arts]
            art_links['Title'] += [x.select_one('div.result_title').text.strip() for x in arts]
            art_links['Skill'] += [skill]*len(arts)
            art_links['Criteria'] += [criteria]*len(arts)
            art_links['Content'] += ['']*len(arts)
            n1 -= len(arts)
            try: 
                elm = driver.find_element(By.CSS_SELECTOR, 'a.button')
                elm.click()
            except Exception:
                break
        df = pd.DataFrame(art_links).drop_duplicates(ignore_index=True)
        return df.head(n)

    def indeed(criteria:str, skill:str, n:int=10)->pd.DataFrame:
        art_links = {x:[] for x in ['Skill', 'Criteria', 'Title', 'Link', 'Content']}
        url = "https://www.indeed.com/career-advice/search?q=" + criteria.replace(' ', '+') + '+' +  skill.replace(' ', '+')
        driver.get(url) 

        #Still not able to access the HTML contents for indeed, so have not been able to work upon it.
        #If a solution is found,the code can be put between the comments below
        #Code begins here

        
        #Code ends here
        df = pd.DataFrame(art_links).drop_duplicates(ignore_index=True)
        return df.head(n)

    def reddit(criteria:str, skill:str, n:int=10)->pd.DataFrame:
        art_links = {x:[] for x in ['Skill', 'Criteria', 'Title', 'Link', 'Content']}
        url = "https://www.reddit.com/search/?q=" + criteria.replace(' ', '%20') + '%20' +  skill.replace(' ', '%20') + '&type=link'
        burl = 'https://www.reddit.com'
        driver.get(url) 

        def pagination(driver):
          scroll_limit = 30
          for i in range(scroll_limit):
                  # Scroll down to bottom
              driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

              # Wait to load page
              time.sleep(0.5)

        pagination(driver) #scroll the page multiple times
        ele = driver.find_elements(By.CSS_SELECTOR, '#AppRouter-main-content > div > div > div._3ozFtOe6WpJEMUtxDOIvtU > div > div > div._2lzCpzHH0OvyFsvuESLurr._3SktesklDBwXt2pEl0sHY8 > div._1BJGsKulUQfhJyO19XsBph._3SktesklDBwXt2pEl0sHY8 > div._1MTbwSHIISfMYM16YhZ8kN > div.QBfRw7Rj8UkxybFpX-USO > div')
        for i in range(len(ele)): 
          soup = self.get_soup(ele[i].get_attribute('outerHTML'))
          details = soup.select_one('div.y8HYJ-y_lTUHkQIc1mdCq._2INHSNB8V5eaWp4P0rY_mE a')
          art_links['Link'].append(burl+details.get('href'))
          art_links['Title'].append(details.find('h3').text.strip())
        art_links['Skill'] = [skill]*len(ele)
        art_links['Criteria'] = [criteria]*len(ele)
        art_links['Content'] = ['']*len(ele)

        df = pd.DataFrame(art_links).drop_duplicates(ignore_index=True)
        return df.head(n)
    
    dom_search = {'medium.com':medium, 'wikihow.com':wikihow, 'indeed.com': indeed, 'reddit.com': reddit}
    combinations = list(itertools.product(criterias,skills,forums))
    for combn in combinations: 
        results = dom_search[combn[2]](combn[0], combn[1], n)
        df = pd.concat([df, results], ignore_index=True)
    driver.close()
    driver.quit()
    return df

#Sample execution code
sa = SearchOptions()
res = sa.forum_search(['improve', 'pitfalls', 'practice'], ['communication skills', 'self awareness'],['medium.com', 'wikihow.com', 'reddit.com'], 20)
res.drop_duplicates(subset=['Skill', 'Title', 'Link'], inplace=True, ignore_index=True)
now = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
filename = now +'.xlsx'
res.to_excel(f'D:\\Git\\Omdena-soft-skills-AI\\Excel files\\g-search-api\\{filename}')
print(tabulate(res, headers = 'keys', tablefmt = 'psql'))
