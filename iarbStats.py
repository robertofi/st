import streamlit as st
from utils import sleep, datetime, timedelta, pd, np, Fore, Style, beep, \
	read_dict, getNextMarketOpen, timezone
from uIbapi.ManageOrders import manageOrders, q_BarSizeStr_to_Timedelta
import IndexArbitrage.funcs as fc
from IndexArbitrage.indexArb import Position
from IndexArbitrage.__main__ import WAIT_TILL, RUN_TILL
st.set_page_config(layout="wide")
# plt.style.use('dark_background')

TOL_LAST_CHECK_WITH_PORTFOLIO = 60
TOL_LAST_CHECK_NO_PORTFOLIO = 600

path = r'G:\My Drive\python\IndexArbitrage\dataPaper/'
pathData = r'G:\My Drive\python\IndexArbitrage\dataBktTest/'
delay = .5

lastHealthCheckOk = datetime.now()
dt_market_open, dt_market_close = getNextMarketOpen()
tz = timezone('America/Sao_Paulo')
dt_market_open, dt_market_close = dt_market_open.astimezone(tz).replace(
	tzinfo=None) + WAIT_TILL + timedelta(
	seconds=120), dt_market_close.astimezone(tz).replace(tzinfo=None) + \
                                  RUN_TILL


def calcPNL(parms):
	di_pm = diPaper[parms]
	dfStrategies = mo._readStrategiesTable(
		tableName=diTables['strategies']['table'])
	symbols = dfStrategies.symbol.to_list()
	dfClose = mm.sql_read_col_table(symbols=symbols, wts=di_pm['wts'],
		BarSizeStr=di_pm['BarSizeStr'],
		dtStart=datetime.now() - q_BarSizeStr_to_Timedelta(
			di_pm['BarSizeStr']) * 3).fillna(method='pad')
	dfStrategies['current'] = dfStrategies.ExecutedQuantity * dfClose.iloc[-1][
		dfStrategies.symbol].values
	dfStrategies[
		'buyPrice'] = dfStrategies.ExecutedQuantity * dfStrategies.OpenPrice
	
	return (dfStrategies['current'] - dfStrategies['buyPrice']).sum()


def styleMap(v):
	if v == 'NOT OK':
		return 'background: darkred'
	elif v == 'none':
		return 'color: green'
	elif v in ['long', 'short']:
		return 'color: yellow'
	elif pd.isna(v):
		return 'color: black'
	else:
		return 'color: white'


def backColor(x, cols):
	return ['background: red' if s in cols else '' for s in x.index]


def highlight_vals(row, col='dist'):
	styles = {col: '' for col in row.index}
	col = 'dist'
	if row[col] > -0.5:
		styles[col] = 'color: lightgreen'
	elif row[col] >= -1.7:
		styles[col] = 'color: yellow'
	elif row[col] < -1.7:
		styles[col] = 'color: red'
	
	if 'PnL' in row.keys():
		col = 'PnL'
		if row[col] is None:
			pass
		elif row[col] > 0:
			styles[col] = 'background-color: darkgreen'
		elif row[col] < 0:
			styles[col] = 'background-color: darkred'
	
	return styles


def healthCheck():
	""" check health stats to see if everything is running and beeps if not"""
	global lastHealthCheckOk, dfOpenTrades, dfWithPortfolios, dfPrcsStats, \
        lastHealthOkElapsed
	
	idx = ['iArbPrcs', 'calcPrcs', 'historyPrcs', 'mktInfoPrcs']
	fHCchekOk = (dfPrcsStats.loc[idx, 'Alive'] == dfPrcsStats.loc[
		idx, 'Total']).all()
	idx = ['Market data farm', 'HMDS data farm', 'Sec-def data farm']
	fHCchekOk *= all(
		[i in dfPrcsStats.index and dfPrcsStats.loc[i, "Alive"] for i in idx])
	fHCchekOk *= (
		not pd.isna(dfOpenTrades.loc[:, ['zLong', 'zShort']].values).any()) \
        if (
			  dfIArbStats['position'] != 'none').any() else True
	fHCchekOk *= (not pd.isna(
		dfWithPortfolios.loc[:, ['zLong', 'zShort']].values).any()) if (
			  dfIArbStats['portfolios'] != 0).any() else True
	
	if fHCchekOk:
		lastHealthCheckOk = datetime.now()
	lastHealthOkElapsed = max((datetime.now() - lastHealthCheckOk).seconds,
	                          min_last_check)
	
	# alert ?
	if ((lastHealthOkElapsed > TOL_LAST_CHECK_WITH_PORTFOLIO and (
		  (dfIArbStats['position'] != 'none').any() or (
		  dfIArbStats['portfolios'] != 0).any())) or (
		      lastHealthOkElapsed > TOL_LAST_CHECK_NO_PORTFOLIO)) and \
          playSound and dt_market_open <= datetime.now() <= dt_market_close:
		beep(1000, 500)


if __name__ == '__main__':
	diTables = dict(logTrades=dict(table='index_arb_log', db='intraday'),
	                strategies=dict(table='strategies', db='intraday'),
	                dfIArbStats=dict(table='iarb_stats', db='intraday'),
	                dfPrcsStats=dict(table='prcs_stats', db='intraday'))
	fileParams = path + 'paperParams.json'
	diPaper = read_dict(fileParams, add='')
	mo = manageOrders(Path=path)
	db = mo.db
	mm = mo.mm
	
	searchResultMap = {'0': f'portfolios found',
		'1': 'Didn´t find any portfolio', '2': 'restrictions on weights',
		'3': 'no cointegrated assets', '4': 'not enough historical bars ',
		'5': 'ETF not available'}
	positionMap = {0: 'none', 1: 'long', 2: 'short', 3: 'ordersPlaced',
		4: 'partial'}
	
	menuScreen = st.sidebar.selectbox('Select', ['production', 'trades'])
	
	if menuScreen == 'production':
		
		tPrcsStats = st.sidebar.dataframe(pd.DataFrame())
		tLastCheck = st.sidebar.text(' ')
		tiOT = st.text('Open Trades')
		tOT = st.text('')
		tiWP = st.text('Found portfolios')
		tWP = st.text('')
		tiNP = st.text('Searching for portfolios')
		tNP = st.text('')
		playSound = st.sidebar.checkbox('Beep', value=True)
		testBeep = st.sidebar.button('beep test')
		if testBeep:
			beep(1000, 500)
		# testBeep = False
		
		colsOT = ['dist', 'position', 'PnL', 'gross', 'zLong', 'zShort',
		          'zHist', 'assets', 'id', 'exit', 'lastCheck', 'dataTimeOk']
		colsWP = ['dist', 'position', 'zLong', 'zShort', 'zHist', 'portfolios',
		          'entry', 'exit', 'lastCheck', 'dataTimeOk']
		colsNP = ['searchResult', 'lastCheck', 'wait', 'dataTimeOk']
		
		while True:
			dfPrcsStats = db.df_from_sql(table=diTables['dfPrcsStats'][
                'table'],
			                             db=diTables['dfPrcsStats']['db'])
			dfIArbStats = db.df_from_sql(table=diTables['dfIArbStats'][
                'table'],
			                             db=diTables['dfIArbStats']['db'])
			dfIArbStats.sort_values(
				by=['position', 'portfolios', 'wait', 'parms'],
				ascending=[False, False, True, True], inplace=True)
			dfIArbStats['searchResult'] = dfIArbStats['searchResult'].map(
				searchResultMap)
			dfIArbStats['dataTimeOk'] = dfIArbStats['dataTimeOk'].map(
				{0: 'NOT OK', 1: 'OK'})
			dfIArbStats['position'] = dfIArbStats['position'].map(positionMap)
			dfIArbStats['lastCheck'] = (datetime.now() - pd.to_datetime(
				dfIArbStats['lastCheck']).dt.tz_localize(
				None)).dt.total_seconds()
			dfIArbStats['wait'] = dfIArbStats.apply(lambda x: (
					  x.wait - datetime.now()).seconds if x.wait > datetime.now() else 0,
			                                        axis=1)
			dfIArbStats.set_index('parms', inplace=True)
			dfPrcsStats.set_index('processes', inplace=True)
			dfIArbStats['zLong'] = pd.to_numeric(dfIArbStats['zLong'],
			                                     errors='coerce')
			dfIArbStats['zHist'] = pd.to_numeric(dfIArbStats['zHist'],
			                                     errors='coerce')
			dfIArbStats['zShort'] = pd.to_numeric(dfIArbStats['zShort'],
			                                      errors='coerce')
			dfIArbStats.insert(0, 'dist', -dfIArbStats.apply(
				lambda x: x.zLong - x.exit if x.position == positionMap[
					Position.short] else -x.zShort - x.exit if x.position ==
				                                               positionMap[
					                                               Position.long] else min(
					x.entry + x.zLong,
					x.entry - x.zShort) if x.portfolios != 0 else np.nan,
				axis=1))
			
			dfIArbStats.loc[dfIArbStats[
				                (dfIArbStats['dataTimeOk'] == 'NOT OK') | (
					                pd.isna(dfIArbStats['searchResult']))
				                ].index,'searchResult'] = ''
			
			dfOpenTrades = \
			dfIArbStats[dfIArbStats['position'] != positionMap[Position.none]][
				colsOT]
			dfOpenTrades.insert(3, 'PnLperc',
			                    dfOpenTrades['PnL'] / dfOpenTrades['gross'])
			dfWithPortfolios = dfIArbStats[
				(dfIArbStats['position'] == positionMap[Position.none]) & (
						  dfIArbStats['portfolios'] > 0)][colsWP]
			dfNoPortfolios = dfIArbStats[
				(dfIArbStats['position'] == positionMap[Position.none]) & (
						  dfIArbStats['portfolios'] == 0)][colsNP]
			
			tiWP.text(f'Found portfolios ({len(dfWithPortfolios)})')
			tiNP.text(f'Searching for portfolios ({len(dfNoPortfolios)})')
			
			if len((dfOpenTrades)) > 0:
				tiOT.text(f'Open Trades ({len(dfOpenTrades)})')
				tOT.dataframe(
					dfOpenTrades.style.bar(subset='dist', vmin=0, vmax=-2.2,
					                       color=['darkgreen', 'darkgreen'],
					                       width=100, align='left').applymap(
						styleMap).apply(lambda x: highlight_vals(x, 'dist'),
					                    axis=1).highlight_min(
						subset=['lastCheck'], color='darkblue').highlight_max(
						subset=['lastCheck'],
                        color='darkgreen').set_properties(
						**{'height': '10'}).format(
						dict(lastCheck=lambda x: f'{x:,.0f}',
						     id=lambda x: f'{x:,.0f}' if x > 0 else '',
						     dist=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     PnL=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     PnLperc=lambda x: f'{x:,.2%}' if not pd.isna(
							     x) else '',
						     gross=lambda x: f'{x:,.0f}' if not pd.isna(
							     x) else '',
						     zLong=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     zShort=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     zHist=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '', assets=lambda
								x: f'{x:,.0f}' if x else '')).set_precision(2))
			else:
				tiOT.text('')
				tOT.text('')
			
			if len((dfWithPortfolios)) > 0:
				
				tWP.dataframe(
					dfWithPortfolios.style.
						bar(subset='dist', vmin=0, vmax=-2.2,
					        color=['darkgreen', 'darkgreen'], width=100,
					        align='left').
						applymap(styleMap).
						apply(lambda x: highlight_vals(x, 'dist'), axis=1).
						highlight_min(subset=['lastCheck'],
						color='darkblue').highlight_max(subset=['lastCheck'],
						color='darkgreen').
						set_properties(**{'height': '10'}).format(
						dict(lastCheck=lambda x: f'{x:,.0f}',
						     dist=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     zLong=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     zShort=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     zHist=lambda x: f'{x:,.2f}' if not pd.isna(
							     x) else '',
						     portfolios=lambda x: f'{x:,.0f}' if x else '')).
						set_precision(2))
			else:
				tWP.text('')
				tiWP.text('')
			
			tNP.dataframe(
				dfNoPortfolios.style.highlight_min(subset=['wait', 'lastCheck'],
				                                   color='darkblue').highlight_max(
					subset=['wait', 'lastCheck'],
					color='darkgreen').set_properties(
					**{'height': '10'}).format(
					dict(lastCheck=lambda x: f'{x:,.0f}', )).set_precision(2),
				2000, 1000)
			
			tPrcsStats.dataframe(dfPrcsStats[['Alive', 'Total']])
			
			min_last_check = min(dfIArbStats["lastCheck"])
			healthCheck()
			msg = f'checked {lastHealthOkElapsed:,.0f}s ago\n' \
			      f'OK: {sum(dfIArbStats["dataTimeOk"] == "OK")}\n' \
			      f'NOT OK: {sum(dfIArbStats["dataTimeOk"] == "NOT OK")}\n'
			for k in positionMap.keys():
				v = sum(dfIArbStats["position"] == positionMap[k])
				if v:
					msg += f'{positionMap[k]}: {v}\n'
			msg += f'Portfolios: {dfIArbStats["portfolios"].sum()}'
			tLastCheck.text(msg)
			sleep(delay)
	
	if menuScreen == 'trades':
		dfstrategiesAll = db.select(table=diTables['strategies']['table'],
		                            db=diTables['strategies']['db']).set_index(
			'id')
		dfLogTrades = db.df_from_sql(table=diTables['logTrades']['table'],
		                             db=diTables['logTrades']['db'])
		dfLogTrades = dfLogTrades[dfLogTrades.id >= 86].set_index('id')
		dfLogTrades.drop(
			list(range(87, 95)) + [100, 101] + list(range(120, 153)) + list(
				range(154, 158)), inplace=True)
		dfLogTrades.insert(0, 'Strategy', dfLogTrades.apply(lambda x:
		                                                    dfstrategiesAll.set_index(
			                                                    'StrategyId').loc[
			                                                    x.name, 'Strategy'].values[
			                                                    0], axis=1))
		tradeId = st.selectbox('Select trade', dfLogTrades.index[::-1])
		cols = dfLogTrades.columns.to_list()
		cols = cols[:2] + cols[-5:] + cols[2:-5]
		
		st.dataframe(
			dfLogTrades.loc[dfLogTrades.index[::-1], cols].style.set_precision(
				2).highlight_min(
				subset=['resultPerc', 'gross', 'pnl', 'assets'],
				color='blue').highlight_max(
				subset=['resultPerc', 'gross', 'pnl', 'assets'],
				color='green').apply(
				lambda x: ['background: darkgreen' if x.name == tradeId else ''
				           for i in x], axis=1).format(
				{'resultPerc': lambda x: f'{x:,.3%}',
				 'gross': lambda x: f'{x:,.0f}', 'pnl': lambda x: f'{x:,.2f}',
				 'dtStart': lambda x: f'{x:%d-%b}' if not pd.isna(x) else '',
				 'dtEnd': lambda x: f'{x:%d-%b}' if not pd.isna(x) else ''}))
		resultPerc = dfLogTrades["resultPerc"].dropna().values
		st.sidebar.text(
			f'trades: {len(resultPerc)}, positive: {(resultPerc >= 0).sum()}, '
            f'negative: {(resultPerc < 0).sum()}\n'
			f'% positive: {(resultPerc >= 0).sum() / len(resultPerc):,.0%}, '
            f'avg res: {resultPerc[resultPerc >= 0].mean():.3%}\n'
			f'% negative: {(resultPerc < 0).sum() / len(resultPerc):,.0%}, '
            f'avg res: {resultPerc[resultPerc < 0].mean():.3%}\n'
			f'net cash: {dfLogTrades["pnl"].sum():,.2f}\n'
			f'total result: {dfLogTrades["resultPerc"].sum():,.3%}, '
			f'{dfLogTrades["resultPerc"].sum() / len(dfLogTrades):,.3%}/trade')
		dfstrategies = dfstrategiesAll[dfstrategiesAll['StrategyId'] ==
                                       tradeId]
		st.dataframe(dfstrategies, 2500, 1000)
		plotBktst = st.sidebar.button('plot backtest')
		if plotBktst:
			fig = fc.plotDiArbRes(Parms=dfstrategies.Strategy.values[0][5:],
			                      returnFig=True)
			the_plot = st.pyplot(fig=fig)
		plotTrade = st.sidebar.button('plot trade')
		if plotTrade:
			fig = fc.calc_and_plot_live_trade(tradeId, plotTrade=True,
			                                  returnFig=True)
			the_plot = st.pyplot(fig=fig)