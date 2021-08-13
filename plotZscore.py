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
fileParams = Path+r'paperParams.json'
Parms = 'IndexArb-xli15mins_04'
pm = Settings(filePath=fileParams, fromKey=Parms)

entryZScore, exitZScore = pm.entryZscore, pm.exitZscore

cols = ['zScoreHist', 'zScoreForLong', 'zScoreForShort', 'portfolios', 'PnL', 'position']
fig,ax = plt.subplots()
dfAllTrades=db.df_from_sql(table='log_zscore', db='intraday', add=f'where date >="{str(datetime.now().date())} 00:00:00"')[-1000:]
# df[['zScoreHist', 'zScoreForLong', 'zScoreForShort']].plot(ax=ax)
lines = [ax.plot(dfAllTrades[col].values)[0] for col in cols[:3]]
ax2 = ax.twinx()
lines += [ax2.plot(dfAllTrades[cols[3]])[0], ax2.plot([], c=(0,0.5,1))[0]]
ax.axhline(0, c='black', ls='dotted')
ax.axhline(entryZScore, ls='dotted')
ax.axhline(-entryZScore, ls='dotted')
ax.axhline(exitZScore, c='r', ls='dotted')
ax.axhline(-exitZScore, c='r', ls='dotted')
the_plot = st.pyplot(fig=fig)
left_column, right_column = st.beta_columns([1,1])
timeWrite=right_column.text(f'{datetime.now()}')
tZscores = st.sidebar.text(' ')
stopSound = st.sidebar.checkbox('No Beep')
st.sidebar.write('Current Portfolio: ')
tWeights = st.sidebar.text(' ')
tTime = st.sidebar.text(' ')
tPNL1 = st.sidebar.text(' ')
tPNL2 = st.sidebar.text(' ')
PnLs = np.full(1000,np.nan)
tRunning = st.sidebar.text(' ')


delays = [0, 1, 3, 15, 30, 60, 120]
default_ix = delays.index(0)
delay = st.sidebar.selectbox('delay to refresh screen, in seconds', delays, index=default_ix)
while True:
  dfAllTrades=db.df_from_sql(table='log_zscore', db='intraday', add=f'where date >="{str(datetime.now().date())} 00:00:00"')[-1000:]
  dfAllTrades['PnL'] = PnLs[-len(dfAllTrades):]
  timeWrite.write(f'{datetime.now():%d/%m - %H:%M:%S}')

  for line,col in zip(lines, cols[:5]):
    line.set_xdata(dfAllTrades.index)
    line.set_ydata(dfAllTrades[col].values)
  ax.relim()
  ax2.relim()
  ax.autoscale_view()
  ax2.autoscale_view()
  ax.draw(renderer=None)
  the_plot.pyplot(fig=fig)
  position = dfAllTrades.iloc[-1]['position']
  portfolios = dfAllTrades.iloc[-1]['portfolios'].astype(int)
  dfAllTrades = dfAllTrades[-10:]
  avgTimeToUpdate = np.mean(np.diff(dfAllTrades['date'])).astype('timedelta64[ms]').astype('float') / 1000
  if datetime.now()-dfAllTrades.iloc[-1]['date'] < timedelta(seconds=20):
    tRunning.write(f'Running')
  else:
    tRunning.write('Stopped')
    if not stopSound: beep(1000, 500)
  dfAllTrades['dt'] = dfAllTrades.date.dt.time
  dfAllTrades = dfAllTrades[['dt'] + cols]
  tZscores.write(dfAllTrades)

  if position != 0:
    dfStrategies = mo._readStrategiesTable(tableName=diTables['strategies']['table'])
    mm.readHistoryCloseFromSql(symbols=dfStrategies.symbol,
                               wts = wts,
                               BarSizeStr=pm.BarSizeStr, updateTillNow=True)
    dfClose = getattr(mm, mm._getDfCloseWtsName(pm.BarSizeStr, wts))
    dfStrategies['current'] = dfStrategies.ExecutedQuantity * dfClose.iloc[-1][dfStrategies.symbol].values
    dfStrategies['buyPrice'] = dfStrategies.ExecutedQuantity*dfStrategies.OpenPrice
    dfStrategies['PNL'] = (dfStrategies['current'] - dfStrategies['buyPrice'])
    PNL = dfStrategies['PNL'].sum()
    dfAllTrades=db.df_from_sql(table='weights', db='intraday')
    tWeights.write(dfAllTrades)
    tTime.write(f'\n Average update {avgTimeToUpdate} seconds')
    tPNL1.write(f'PNL: {PNL:,.2f}')
    tPNL2.write(dfStrategies[["symbol","PNL"]])
    PnLs = np.roll(PnLs, -1)
    PnLs[-1] = PNL

  else:
    tWeights.write(f'searching on {portfolios} portfolios.')
    tTime.write(f'\n Average update {avgTimeToUpdate} seconds')
    tPNL1.write(' '*50)
    tPNL2.write(' '*50)
    PnLs[:] = np.nan



  sleep(delay)
