import sys, os
if sys.executable.endswith('pythonw.exe'):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.path.join(os.getenv('TEMP'), 'stderr-{}'.format(os.path.basename(sys.argv[0]))), "w")
    
from flask import Flask, url_for, Response, request, render_template, session, redirect, flash
import requests
from requests import get
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
import warnings
warnings.filterwarnings('ignore')
from pmdarima.arima import auto_arima
import ctypes
from flaskwebgui import FlaskUI

app = Flask(__name__)
ui = FlaskUI(app, width=1800, height=1000)
app.secret_key = b'8A\x0e\x00=\xab\xb7P9s\x89/'
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('WebScraping.html')

global Items
Items = None
@app.route('/webscrape', methods=("POST", "GET"))
def webscrape():
    if request.method == 'POST':
        # declare empty lists
        name, sold = [], []
        i = 1
        for i in range(1,5):
            # create object for chrome options
            chrome_options = webdriver.ChromeOptions()
            base_url = 'https://shopee.com.my/mall/Groceries-Pets-cat.2600/popular?pageNumber=' + str(i)

            # set chrome driver options to disable any popup's from the website
            # to find local path for chrome profile, open chrome browser
            # and in the address bar type, "chrome://version"
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('disable-notifications')
            chrome_options.add_argument('start-maximized')
            # To disable the message, "Chrome is being controlled by automated test software"
            chrome_options.add_argument("disable-infobars")
            # Pass the argument 1 to allow and 2 to block
            chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
            # invoke the webdriver
            browser = webdriver.Chrome(ChromeDriverManager().install(),chrome_options=chrome_options)
            browser.get(base_url)
            delay = 5 #secods
          
            while True:
                try:
                    WebDriverWait(browser, delay)
                    print ("Page is ready")
                    sleep(5)
                    html = browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
                    #print(html)
                    soup = BeautifulSoup(html, "html.parser")

                    # find_all() returns an array of elements. 
                    # We have to go through all of them and select that one you are need. And than call get_text()
                    for item_n in soup.find_all('div', class_='PFM7lj'):
                        name.append(item_n.text)

                    # find total number of items sold
                    for item_s in soup.find_all('div', class_='go5yPW'):
                        sold.append(item_s.text)

                    break # it will break from the loop once the specific element will be present. 
                except TimeoutException:
                    print ("Loading took too much time!-Try again")
                    
        if len(name) !=0 and len(sold) !=0:
            global Items
            Items = pd.DataFrame({
            'Item name': name,
            'Item sold': sold,
            })
            Items['Item sold'] = Items['Item sold'].str[:-5]
            Items['Items Check'] = Items['Item sold'].str.strip().str[-1].str.match('k')
            Items.drop(Items[Items['Items Check'] != True].index, inplace = True) 
            Items.reset_index(drop=True)
            Items.loc[Items['Item sold'].str.strip().str[-1] == 'k', 'Item sold'] = Items['Item sold'].str[:-1].astype(float).multiply(1000)
            Items = Items.drop(columns=['Items Check'])
            Items['Item sold'] = Items['Item sold'].astype(int)
            Items = Items.drop_duplicates(subset=['Item name'])
        else:
            flash("Please Scrape Again!")
            render_template('WebScraping.html')
        return render_template('WebScraping.html',  tables=[Items.to_html(classes='data')])
    return render_template('WebScraping.html') 

@app.route('/downloadwebscrape', methods=("POST", "GET"))
def downloadwebscrape():
    if request.method == 'POST':
        if Items is not None and not Items.empty:
            resp = Response(Items.to_csv(index = False))
            resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
            resp.headers["Content-Type"] = "text/csv"
            return resp
        else:
            flash("Please Scrape The Data First!")
            render_template('WebScraping.html')
    return render_template('WebScraping.html')

global merge1
merge1 = None
@app.route('/mergeupload1', methods=['GET', 'POST'])
def mergeupload1():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            global merge1
            merge1 = pd.read_csv(file)
            return render_template('Merging.html', tables=[merge1.to_html(classes='data')])
        else: 
            flash("Please upload a csv file!")
            render_template('Merging.html')
    return render_template('Merging.html')

global merge2
merge2 = None
@app.route('/mergeupload2', methods=['GET', 'POST'])
def mergeupload2():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            global merge2
            merge2 = pd.read_csv(file)
            return render_template('Merging.html', tables=[merge2.to_html(classes='data')])
        else: 
            flash("Please upload a csv file!")
            render_template('Merging.html')
    return render_template('Merging.html')

global result
result = None
@app.route('/merge', methods=['GET', 'POST'])
def merge():
    if request.method == 'POST':
        if merge1 is not None and not merge1.empty and merge2 is not None and not merge2.empty:
            global result
            result = pd.merge(merge1, merge2, how="outer", on=["Item name"])
            # To rename the item sold name as 1, 2, 3, 4...
            for j in range(len(result.columns)-1):
                j = j + 1
                old = result.columns[j]
                new = j
                result = result.rename(columns = {old:new})
            # To change the column into int type and fill nan with 0
            for j in range(len(result.columns)-1):
                j = j + 1
                result[j] = result[j].fillna(0).astype(int)
            return render_template('Merging.html', tables=[result.to_html(classes='data')])
        else:
            flash("Please Make Sure You Uploaded Both Data!")
            render_template('Merging.html')
    return render_template('Merging.html')

@app.route('/downloadmerge', methods=("POST", "GET"))
def downloadmerge():
    if request.method == 'POST':
        if result is not None and not result.empty:
            resp = Response(result.to_csv(index = False))
            resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
            resp.headers["Content-Type"] = "text/csv"
            return resp
        else:
            flash("Please Merge The Data First!")
            render_template('Merging.html')
    return render_template('Merging.html')

global arima
arima = None
@app.route('/arimaupload', methods=['GET', 'POST'])
def arimaupload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            global arima
            arima = pd.read_csv(file)
            return render_template('ArimaAnalysis.html', tables=[arima.to_html(classes='data')])
        else: 
            flash("Please upload a csv file!")
            render_template('ArimaAnalysis.html')
    return render_template('ArimaAnalysis.html')

@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    if request.method == 'POST':
        if arima is not None and not arima.empty and (arima.shape[1] >= 22):
            # Split the first column with others to enable diff() into dfs[0] and dfs[1]
            dfs = np.split(arima, [1], axis=1)
            # To find the different between previous and the next columns
            dfs[1] = dfs[1].diff(axis=1)
            # Drop the first column which would be nan take note that 1 might be string / int
            dfs[1].drop('1', inplace=True, axis=1)
            # Replace negative values in column with 0
            dfs[1][dfs[1] < 0] = 0
            # Concat the splitted dataframe
            dfcleaned = pd.concat([dfs[0], dfs[1]], axis=1)
            # Rename the columns again
            for j in range(len(dfcleaned.columns)-1):
                j = j + 1
                old = dfcleaned.columns[j]
                new = j
                dfcleaned = dfcleaned.rename(columns = {old:new})
            # To split "Item Name" and other columns to two dataframes
            frame = []
            name = []
            # Loop all column to get name and split
            for col in dfcleaned.columns: 
                if col != "Item Name":
                  frame.append(col)
                else:
                  name.append(col)    
            salescol = dfcleaned[frame].copy()
            finaldf = dfcleaned[name].copy()
            # split dataframe by row 
            splits = [salescol.loc[[i]] for i in salescol.index] 
            listostoreprediction=[]
            for i in range(len(salescol)):
                # view smaller dataframe 
                #print(splits[i])
                # Swap column to row and rename the column
                df_arima = splits[i].transpose().rename(columns = {i:"Item Sold"})
                arima_model =  auto_arima(df_arima, m=7)
                value = arima_model.predict(n_periods = 1)[0]
                listostoreprediction.append(value)
            finaldf['Predict Item sold'] = listostoreprediction
            value1 = finaldf['Predict Item sold'].argmax()
            Toresult = [{'Begin': 'The recommended food product is ',
            'result': finaldf['Item Name'][value1],
            'connect': ' with the predicted sales of ',
            'number': round(finaldf['Predict Item sold'][value1]),
            'end': '.',}]
            #print(finaldf['Item Name'][value1])
            return render_template('ArimaAnalysis.html', tables=[dfcleaned.to_html(classes='data')], Toresult=Toresult)
        else:
            flash("Please upload a csv file or a csv file with at least 21 columns of sales data!")
            render_template('ArimaAnalysis.html')
    return render_template('ArimaAnalysis.html')

if __name__ == '__main__':
    ui.run()
    #app.run(debug=True)