# This is a sample Python script.

import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
st. set_page_config(layout="wide")

from utils import *
from uIbapi.ManageOrders import manageOrders
from database import dbaccess
Path=r'G:\My Drive\python\IndexArbitrage\dataPaper/'
diTables = dict(weights=dict(table='weights', db='intraday'),
      strategies=dict(table='strategies', db='intraday'), log_zscore=dict(table='log_zscore', db='intraday'),
      logTrades=dict(table='index_arb_log', db='intraday'))
mo = manageOrders(Path=Path)
db = mo.db
mm = mo.mm
wts = 'TRADES'
fileParams = Path+r'paperParams.py'
Parms = 'IndexArb-19'
pm = Settings(filePath=fileParams, fromKey=Parms)

entryZScore, exitZScore = pm.entryZscore, pm.exitZscore

cols = ['zScoreHist', 'zScoreForLong', 'zScoreForShort', 'portfolios', 'position']
fig,ax = plt.subplots()
df=db.df_from_sql(table='log_zscore', db='intraday', add=f'where date >="{str(datetime.now().date())} 00:00:00"')[-1000:]
# df[['zScoreHist', 'zScoreForLong', 'zScoreForShort']].plot(ax=ax)
lines = [ax.plot(df[col].values)[0] for col in cols[:3]]
ax2 = ax.twinx()
lines += [ax2.plot(df[cols[3]])[0]]
ax.axhline(0, c='black', ls='dotted')
ax.axhline(entryZScore, ls='dotted')
ax.axhline(-entryZScore, ls='dotted')
ax.axhline(exitZScore, c='r', ls='dotted')
ax.axhline(-exitZScore, c='r', ls='dotted')
the_plot = st.pyplot(fig=fig)
left_column, right_column = st.beta_columns([1,1])
timeWrite=right_column.text(f'{datetime.now()}')
tZscores = st.sidebar.text(' ')
st.sidebar.write('Current Portfolio: ')
tWeights = st.sidebar.text(' ')
tTime = st.sidebar.text(' ')
tNav1 = st.sidebar.text(' ')
tNav2 = st.sidebar.text(' ')
tRunning = st.sidebar.text(' ')

while True:
  df=db.df_from_sql(table='log_zscore', db='intraday', add=f'where date >="{str(datetime.now().date())} 00:00:00"')[-1000:]
  timeWrite.write(f'{datetime.now():%d/%m - %H:%M:%S}')

  for line,col in zip(lines, cols[:4]):
    line.set_xdata(df.index)
    line.set_ydata(df[col].values)
  ax.relim()
  ax2.relim()
  ax.autoscale_view()
  ax2.autoscale_view()
  ax.draw(renderer=None)
  the_plot.pyplot(fig=fig)
  position = df.iloc[-1]['position']
  portfolios = df.iloc[-1]['portfolios'].astype(int)
  df = df[-10:]
  avgTimeToUpdate = np.mean(np.diff(df['date'])).astype('timedelta64[ms]').astype('float')/1000
  if datetime.now()-df.iloc[-1]['date'] < timedelta(seconds=8):
    tRunning.write(f'Running')
  else:
    tRunning.write('Stopped')
    beep(1000, 500)
  df['dt'] = df.date.dt.time
  df = df[['dt']+cols]
  tZscores.write(df)

  if position != 0:
    dfStrategies = mo._readStrategiesTable(tableName=diTables['strategies']['table'])
    mm.readHistoryCloseFromSql(symbols=dfStrategies.symbol,
                               wts = wts,
                               BarSizeStr=pm.BarSizeStr, updateTillNow=True)
    dfClose = getattr(mm, mm._getDfCloseWtsName(pm.BarSizeStr, wts))
    dfStrategies['current'] = dfStrategies.ExecutedQuantity * dfClose.iloc[-1][dfStrategies.symbol].values
    dfStrategies['buyPrice'] = dfStrategies.ExecutedQuantity*dfStrategies.OpenPrice
    dfStrategies['PNL'] = (dfStrategies['current'] - dfStrategies['buyPrice'])
    NAV = dfStrategies['PNL'].sum()
    df=db.df_from_sql(table='weights', db='intraday')
    tWeights.write(df)
    tTime.write(f'\n Average update {avgTimeToUpdate} seconds')
    tNav1.write(f'NAV: {NAV:,.2f}')
    tNav2.write(dfStrategies[["symbol","PNL"]])

  else:
    tWeights.write(f'searching on {portfolios} portfolios.')
    tTime.write(f'\n Average update {avgTimeToUpdate} seconds')
    tNav1.write(' '*50)
    tNav2.write(' '*50)



  sleep(0.25)
