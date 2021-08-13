# This is a sample Python script.

import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.

from sabido.rotinascoint import *

ls = cointegration(directory='G:/My Drive/algo-trading2/Cointegration_Robot/cointegration_tables_sp500_production/')
ls.tws_clientId_info = 103
open_pos,closed_pos=True,False
# print(f'{datetime.now()}: waiting {args.wait} minutes')

ls.read_df_pairs_on_trade()
ls.read_df_pairs_traded()
diFigs = ls.plot_trades(open_pos, closed_pos, returnAxAndFigs=True)
# st.pyplot(clear_figure=True)
the_plot = st.pyplot(diFigs['openPositions']['fig'])
left_column, right_column = st.beta_columns([1,1])
timeWrite =   right_column.text(f'{datetime.now()}')
# checkPairs = left_column.button('Check Pairs')
# if checkPairs:
#   ls.search_for_buying_oportunities()
#   ls.ChangePairsOnWatchSimpleGui()
while True:
  ls.read_df_pairs_on_trade()
  ls.read_df_pairs_traded()
  plt.close('all')
  diFigs = ls.plot_trades(open_pos, closed_pos, returnAxAndFigs=True)
  # st.pyplot(clear_figure=True)
  the_plot.pyplot(diFigs['openPositions']['fig'])
  # pressed = left_column.button('Press me?')
  timeWrite.write(f'{datetime.now():%d/%m - %H:%M:%S}')

  sleep(3)

#
#
# st.title('My first app')
# st.write("Here's our first attempt at using data to create a table:")
# df = pd.DataFrame({
#   'first column': ['aaa','b','c','d'],
#   'second column': [10, 20, 30, 40]
# })
#
# df
# chart_data = pd.DataFrame(
#      np.random.randn(20, 3),
#      columns=['a', 'b', 'c'])
#
# st.line_chart(chart_data)
#
# map_data = pd.DataFrame(
#     np.random.randn(1000, 2) / [50, 50] + [37.76, -122.4],
#     columns=['lat', 'lon'])
# st.map(map_data)
#
# if st.checkbox('Show dataframe'):
#     chart_data = pd.DataFrame(
#        np.random.randn(20, 3),
#        columns=['a', 'b', 'c'])
#
#     chart_data
#
# option = st.sidebar.selectbox(
#     'Which number do you like best?',
#      df['first column'])
#
# 'You selected:', option
# left_column, right_column = st.beta_columns(2)
# pressed = left_column.button('Press me?')
# if pressed:
#     right_column.write("Woohoo!")
#
# expander = st.beta_expander("FAQ")
# expander.write("Here you could put in some really, really long explanations...")
#
# import matplotlib.pyplot as plt
#
# import numpy as np
#
# arr = np.random.normal(1, 1, size=100)
#
# fig, ax = plt.subplots()
#
# ax.hist(arr, bins=20)
#
# st.pyplot(fig)