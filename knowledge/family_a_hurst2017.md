---
family: A
source: hurst2017
doc_type: pdf
reliability: 95
date: 2017
tickers: []
ingested: 2026-06-27
---

A Century of Evidence on Trend-Following Investing
Brian Hurst, Yao Hua Ooi, and Lasse Heje Pedersen
Brian Hurst is principal at AQR Capital Management, Greenwich, CT
Email: Brian.Hurst@aqr.com
Yao Hua Ooi is principal at AQR Capital Management, Greenwich, CT
Email: Yao.Ooi@aqr.com
Lasse Heje Pedersen is principal at AQR Capital Management, and a Professor at Copenhagen Business School and New York
University
Email: lhp001@gmail.com
Acknowledgment: We are grateful to Cliff Asness and John Liew for helpful discussions, and to Ari Levine, Abhilash Babu, David
McDiarmid, Haitao Fu, and Vineet Patil for excellent research assistance.

Abstract
In this article, the authors study the performance of trend-following investing across global markets since 1880, extending the existing evidence by more than 100 years using a novel data set. They find that in each decade since
1880, time series momentum has delivered positive average returns with low correlations to traditional asset classes. Further, time-series momentum has performed well in 8 out of 10 of the largest crisis periods over the century, defined as the largest drawdowns for a 60/40 stock/bond portfolio. Lastly, time series momentum has performed well across different macro environments, including recessions and booms, war and peacetime, highand low-interest rate regimes, and high- and low-inflation periods.

Electronic copy available at: https://ssrn.com/abstract=2993026

As an investment style, trend following has existed for a very long time. Some 200 years ago, the classical economist David Ricardo’s imperative to “cut short your losses” and “let your profits run on” suggests an attention to trends. A century later, the legendary trader Jesse Livermore stated explicitly that the “big money was not in the individual fluctuations but in ... sizing up the entire market and its trend.”1
The most basic trend-following strategy is time series momentum — going long markets with recent positive returns and shorting those with recent negative returns.

The literature shows that time series momentum has been profitable on average since 1985 for nearly all equity index futures, fixed income futures, commodity futures, and currency forwards.2 The strategy explains the strong performance of managed futures funds from the late 1980s, when fund returns and index data first become available,3 and captures most forms of trend-following investing.4
In this article, we seek to establish whether the strong performance of trend following is a statistical fluke of the last few decades or a more robust phenomenon that exists over a wide range of economic conditions.

We construct a time-series momentum strategy all the way back to 1880 using historical data from a number of sources, including novel data on commodity futures prices that we hand collect and transcribe from annual reports of the
Chicago Board of Trade.5
We find that time series momentum has been consistently profitable throughout the past 137 years. We examine the strategy’s decade-by-decade performance, its correlation to major asset classes, and its performance in historical equity bull and bear markets. This wealth of data also provides context for evaluating how the strategy
1 Ricardo's trading rules are discussed by Grant [1838] and the quote attributed to Livermore is from Lefèvre [1923].

2 The original work on trend-following investing and hedge funds was due to Fung and Hsieh [1997, 2001]. We follow the time series momentum methodology of Moskowitz, Ooi and Pedersen [2012]. Research on trends also includes Cutler, Poterba and
Summers [1991], Silber [1994], Erb and Harvey [2006], Menkhoff, Sarno, Schmeling, and Schrimpf, [2012], Baltas and Kosowski
[2013, 2015], and Georgopoulou and Wang [2016]. 3 See Fung and Hsieh [2001] and Hurst, Ooi and Pedersen [2013]. 4 Levine and Pedersen [2016] show that time-series momentum in its most general form can capture moving average crossover signals and all other linear trend filters. 5 See also Greyserman and Kaminski [2014] who consider a very long trend-following strategy based on spot prices.

While returns computed based on spot prices are not implementable (because they do not include the effects of the futures “roll down”, e.g., even if spot prices exhibit trends, trend-following investing in futures would not be profitable if the futures prices anticipate the trend, on average), our actual futures data allows us to construct a realistic and implementable version of the strategy. Our century of evidence for time series momentum also complements the evidence that cross-sectional momentum (a closely related strategy based on a security’s performance relative to its peers) has delivered positive returns in individual equities back to 1866 (Chabot, Ghysels and Jagannathan [2009]) and has worked across asset classes (Asness, Moskowitz and Pedersen [2012]).

Electronic copy available at: https://ssrn.com/abstract=2993026

performs across various macroeconomic environments, such as recessions vs. booms, war vs. peacetime, high vs. low interest rate regimes, high vs. low volatility periods, high vs. low inflation periods, and high vs. low correlation periods. While the strategy has historically performed well across most of these economic environments, the characteristic that appears to have affected the performance the most is correlation, where the strategy has performed the best during low correlation environments. We also estimate the effects of fees and transaction costs, and evaluate the benefits of allocating to a trend-following strategy from a traditional stock/bond portfolio.

Data
In our analysis, we use monthly returns for 67 markets across four major asset classes: 29 commodities, 11 equity indices, 15 bond markets, and 12 currency pairs. In order to study the broadest set of markets over the longest time series where we can find data, we combine a large number of existing datasets and hand collect new data that has not been studied previously, to our knowledge. In particular, we construct a novel dataset of daily commodities futures prices by manually transcribing the “Annual Report of the Trade and Commerce of the
Chicago Board of Trade” going back as early as 1877. The hand collected data extends to 1951, where electronic data sets become available. For the study, we use a monthly sample, based on end-of-month prices and returns.

We construct a monthly time series of futures returns by simulating that we hold, and “roll,” one of the most liquid futures contracts. In particular, we “roll” by simultaneously performing two trades: (i) selling out of the futures contract that we previously held, and (ii) buying the next futures contract, collecting the current prices of both contracts to make the analysis as realistic as possible. We focus on closing prices whenever these are available, but in the early sample, we only have access to high and low prices, so we use an average of these. For all markets, we use futures returns when they are available, but for asset classes other than commodities, futures are not available back to 1877.

Hence, prior to the availability of futures data, we rely on cash index returns financed at local short-term interest rates for each country. Our time series momentum strategy requires three

years of past data to estimate volatilities (as described in more detail below) so our sample of simulated strategy returns runs from 1880 to the end of 2016. We do not have data on each of the 67 markets during each month in this sample so we construct the trend-following strategies using the set of assets for which return data exist at each point in time. Appendix A shows which markets for which we have data at each point in time and the respective data sources for each market and each time period.6
Constructing the Time Series Momentum Strategy
Trend-following investing involves going long markets that have been rising and going short markets that have been falling, betting that those trends continue.

We create a time series momentum strategy that is simple, without many of the often arbitrary choices of more complex models. Our methodology follows that of Moskowitz, Ooi and Pedersen [2012] and Hurst, Ooi and Pedersen [2013] and can thus be viewed as an out-of-sample test of those papers. These papers find that time series momentum captures well the performance of the managed futures indices and manager returns, including the largest funds, over the past few decades when data on such funds exists. Specifically, we construct an equal-weighted combination of 1-month, 3-month and 12-month time series momentum strategies for the 67 markets cited above — from as far back as January 1880 to December 2016. The strategy is rebalanced each month as follows.

For each of the three time series momentum strategies, the position taken in each market is determined by assessing the past return in that market over the relevant look-back horizon. A positive past excess return is considered an “up” trend and leads to a long position; a negative past excess return is considered a “down” trend and leads to a short position. Therefore, each strategy always holds either a long or
6 While we have attempted to create as realistic a simulation as possible, we are not claiming that this strategy would have been implementable as described back in the 1880s. Modern day financing markets didn’t exist then, nor did equity index and bond futures markets which are simulated in this study.

The commodities data throughout are based on traded commodities futures prices and is therefore the most realistic, and by the 1980s most of the returns are based on futures prices. The main point of the study is to show that markets have exhibited statistically significant trends for well over a century.

short position in every market. Each position is sized to target the same amount of volatility, both to provide diversification and to limit the portfolio risk from any one market. The positions across the three strategies are aggregated each month and scaled such that the combined portfolio has an annualized ex ante volatility target of
10% annualized.7 The volatility scaling procedure ensures that the combined strategy targets a consistent amount of risk over time, regardless of the number of markets that are traded at each point in time. Finally, we subtract transaction costs and fees.

Our transaction cost estimates are based on recent estimates of average transaction costs in each of the four asset classes, as well as an estimate of how much higher transaction costs were historically compared with the present, based on Jones [2002]. We note the transaction costs are estimated with a significant amount of uncertainty and the strategy may also be subject to other costs such as the costs of “rolling” futures contracts, which are not accounted for in our simulations. To simulate fees, we apply a
2% management fee and a 20% performance fee subject to a high-water mark, as has been typical for hedge funds.8 Details on transaction costs and fee simulations are given in Appendix B.

Performance over a Century
Exhibit 1 shows the performance of the time series momentum strategy over the full sample since 1880, as well as for each decade over this time period. We report the results gross and net of simulated transaction costs, and consider returns both before and after fees. The performance has been surprisingly consistent over an extensive time horizon that includes the Great
Depression, multiple recessions and expansions, multiple wars, stagflation, the Global Financial Crisis, and periods of rising and falling interest rates. Our long-term out-of-sample evidence suggests that it is unlikely that
7 A simple covariance matrix estimated using rolling 3-year (equally weighted) monthly returns is used in the portfolio volatility scaling process.

8 While a 2/20 fee structure has been commonplace in the industry, some managers charged higher management and performance fees in earlier time periods. On the other hand, there are also managers that charge lower fees for the strategy today.

the existence of price trends in markets is a product of statistical randomness or data mining. Indeed, the first 10
decades of data is out-of-sample evidence relative to the literature, and the performance remains strong during this period. Trends thus appear to be a pervasive characteristic of speculative financial markets over the long term. Time series momentum strategies perform well only if prices trend more often than not. A large body of research9
suggests that price trends exist in part due to long-standing behavioral biases exhibited by investors, such as anchoring and herding, as well as the trading activity of non-profit-seeking participants, such as central banks and corporate hedging programs.

For instance, when central banks intervene to reduce currency and interest-rate volatility, they may slow down the rate at which information is incorporated into prices, thus creating trends. The fact that trend-following strategies have performed well historically indicates that these behavioral biases and nonprofit-seeking market participants have likely existed for a long time. To study the robustness and source of these results, Exhibit 2 considers the performance separately for the 1month, 3-month, and 12-month signals. We see that trend-following at each of these horizons has delivered positive returns in each decade. To further study the robustness and ability to implement these strategies, we consider a version where the signal is lagged a month.

In other words, if the trend signal is computed at the last trading day of January, then we assume that we trade on this signal only at the end of February (in the same year). As seen in Exhibit 2, these strategies also deliver positive returns in most decades, but the performance naturally deteriorates with the lagging, especially for the shorter-term signals. Given the consistent performance of the strategy over time, it is also interesting to study the consistency across markets. For this, Exhibit 3 reports the risk-adjusted returns (as measured by the Sharpe ratio) of each of the 67
9 Barberis, Shleifer and Vishny [1998], Daniel, Hirshleifer, Subrahmanyam [1998], De Long et al.

[1990], Hong and Stein [1999]
and Frazzini [2006] discuss a number of behavioral tendencies that lead to the existence of price trends.

markets included in our time series momentum strategy over the full sample from 1880-2016. We see that the strategy has delivered positive average returns in each market, with an average Sharpe ratio of approximately 0.4. We next consider the out-of-sample evidence for individual markets relative to the initial time series momentum study of Moskowitz, Ooi and Pedersen [2012], who used data starting in 1985. To do this, Exhibit 4 reports the performance of each market before 1985, including only markets with at least 10 years of data during this subsample, 1880-1984. Again, we see a remarkably consistent performance across markets and asset classes.

Performance during Crises Periods
The returns to the strategy have exhibited low correlations to stocks and bonds over the full time period, as well as in each decade, as shown in Exhibit 1. Even more impressively, the strategy has performed best in large equity bull and bear markets. Exhibit 5 shows the annual simulated returns to the strategy, plotted against the returns to the U.S. equity market from 1880–2016. The “smile” shows that trend following has done particularly well in extreme up or down years for the stock market, echoing results from the recent decades (Fung and Hsieh [1997]
and Moskowitz, Ooi and Pedersen [2012]).

This strong performance in bear markets over the century extends the evidence that has been documented since the 1980s, as exemplified most recently with the strong performance of trend following during the Global Financial Crisis. As another way to evaluate the diversifying properties of trend following during crises periods, we consider the performance during peak-to-trough drawdowns for the traditional 60/40 portfolio, which invests 60% in US
equities and 40% in US bonds.10 Exhibit 6 shows the performance of the time series momentum strategy during the 10 largest drawdowns experienced by this 60/40 portfolio over the past 137 years.

We see that the time series momentum strategy experienced positive returns in 8 out of 10 of these stress periods and delivered significant
10 The 60/40 portfolio has 60% of the portfolio invested in the U.S. Equity Market and 40% invested in U.S. 10-year government bonds. The portfolio is rebalanced to the 60/40 weights at the end of each month, and no fees or transaction costs are subtracted from the portfolio returns.

positive returns during a number of these events. Hence, the valuable diversification benefits that trend-following strategies delivered during the 2007–2009 Global Financial Crisis may represent a more general pattern when you consider how the strategy has behaved in other deep bear markets over the century. Why have trend-following strategies tended to do well in bear markets? The intuition is that most bear markets have historically occurred gradually over several months, rather than abruptly over a few days, which allows trend followers an opportunity to position themselves short after the initial market decline and profit from continued market declines.

In fact, the average peak-to-trough drawdown length of the 10 largest 60/40 drawdowns between
1880 and 2016 was approximately 15 months. In contrast, the strategy may not perform as consistently in bear markets that occur very rapidly, such as the 1987 stock market crash, since the strategy may not be able to take positions quickly enough to benefit from sharp market movements in those environments. Nevertheless, the tendency for the strategy to do well on average in major bear markets, while still achieving a positive return on average, makes it a valuable diversifier for investor portfolios.

Given the attractive returns and diversifying characteristics of a time series momentum strategy, allocating to this strategy would have improved a traditional portfolio’s performance over the past 137 years. Specifically, Exhibit
7 shows the simulated effect of allocating 20% of the capital from a 60/40 portfolio to the time series momentum strategy. We see that such an allocation would have helped reduce the maximum portfolio drawdown, lowered portfolio volatility and increased portfolio returns. We can also consider the stress periods for time series momentum (rather than the stress periods for the overall market), which tend to be associated with periods of sharp reversals across multiple markets, or prolonged periods where many markets exhibit a lack of clear trends.

Specifically, Exhibit 8 shows the 10 largest drawdowns for the time series momentum strategy, including the amount of time the strategy took to realize and recover from each drawdown. The drawdown is computed as the percentage loss since the strategy reached its highest-ever

cumulative return (its high-water mark). Naturally, the strategy has experienced significant drawdowns, losing up to 25%, over extended time periods. Performance across Economic Environments
We next consider the performance across different economic environments. This is interesting both to understand the nature of the strategy and to analyze the potential diversification benefits of the strategy. Indeed, investors benefit most from strategies that deliver high returns during “tough times” when their marginal utility of wealth is high. We have already considered the performance during crises periods as defined by drawdowns by 60/40, but several other economic environments are of interest.

Exhibit 9, Panel A considers the performance of time series momentum across different regimes, starting with the two classic macroeconomic characteristics (or themes), growth and inflation. To analyze macroeconomic growth, we separate the months into recessions and booms as defined by the NBER Business Cycle Dating Committee. We see that the performance is similar across these environments. The average excess return has been slightly higher during booms, but the difference is not statistically significant. Next, the exhibit reports the performance across low vs. high inflation environments and, again, we find very similar performance for time series momentum.

The strong performance during recessions and during different inflation regimes is evidence of the historical diversifying properties of the strategy. It is also interesting to consider the performance during “tough times” in the sense of war time. There have been so many conflicts around the world that defining wartime and peacetime is not straightforward. To have a clearcut definition, we focus on the largest wars – defined as those with more than 1 million casualties with at least three nations at war – which are World War 1, World War 2, Vietnam War, and Korean War, with “peace” being all other time periods (again, despite the numerous other conflicts). We see that the strategy has performed

similarly across both samples. If anything, the performance has been better during major wars, but the difference is not statistically significant. Lastly, the table considers bull markets vs. bear markets, where bear markets are defined as periods where peak to trough drawdown of U. S. equity market is greater than 20% and bull markets are all other times. The strategy has performed better in bear markets, but the difference is only marginally significant, and perhaps the more robust result is the smile curve in Exhibit 5. Exhibit 9, Panel B considers the same economic environments, but now the economic environment is lagged by
1 month.

For example, this panel considers the performance of trend-following investing during the month after a recession month (so the month where the return is calculated might, or might not, continue to be a recession). Panels A and B thus address different issues: Panel A takes the perspective of an investor who stands at the end of each month, looking back at the performance of trend-following in relation to the economic environment experienced during the same month. This perspective cannot be used to make timing decisions in the portfolio since the economic environment was not known ahead of time.

In contrast, Panel B takes the perspective of an investor who stands at the beginning of each month, looking at the performance of trend-following in the coming month in relation to the economic environment experience in the previous month. Such a prospective analysis could in principle be used to time a trading strategy, but we note several caveats. First, certain variables are not known in real time (e.g., the dating of recessions) and, second, the classification of low vs. high inflation is performed ex post. In any event, Panel B shows that the performance of trend-following was similar across groups.

Hence, while Panel B shows that it appears difficult to improve the strategy via timing decisions, the good news from Panel A is that the strategy appears to be relatively robust across various economic environments.

Exhibit 10 considers different economic indicators, where we can separate the time periods into quintiles (because each of these indicators are numerical, in contrast to binary variables such as war/peace or recession/boom). In particular, we consider the S&P volatility (estimated over the past 36 months), the 3-month change in the estimated volatility, the average absolute pairwise correlations across the markets traded in the portfolio, and the
T-bill yield. Panel A reports the contemporaneous time series momentum performance, while Panel B reports the performance in the following month (or, said differently, the economic indicator is lagged one month, as in Exhibit
9, Panel B).

Starting with the first row of Panel A, we see that time series momentum has performed best in quintiles 3 and 2
where the contemporaneous S&P500 volatility was average or just below average, although this result could also simply reflect randomness in the data. Further, the performance has been similar across quintiles based on changes in equity market volatility and the level of Treasury bill yields. While some practitioners have described trendfollowing as a strategy that is “long volatility”, the quintile sorts on changes in equity volatility show that the performance of the strategy has historically been relatively consistent across periods of increasing and decreasing market volatility.

Looking at the pairwise correlations across markets, we see that lower correlations appear to have been associated with better performance. Turning to Panel B, we see a similar pattern, which could be related to the persistence of the economic indicators. Again the only indicator with a monotonic relation to the performance of time series momentum is the pairwise correlation across markets. We see that low lagged correlations are associated with higher average future returns, while high correlations are associated with low returns. To understand this finding, note first that, for given notional exposures, a higher correlation implies a higher risk at the portfolio level.

However, since our portfolio construction methodology seeks to target a constant volatility, this effect is “undone” by reducing all position sizes when correlations are high. These lower position sizes in turn may lead to lower average returns, which can

help explain why the strategy performs worse during times of high correlations. Said differently, when correlations are high, there are fewer truly different trends to bet on. Exhibit 11 plots the time series of the average absolute pairwise correlation across all the markets used in our strategy. We see that the average correlations have been relatively stable over time, but increased meaningfully from late 2008 until the middle of 2014. During this period, the many markets moved together based on “riskon/risk-off,” leading to higher correlations both within and across asset classes. Conclusion
Trend-following investing has performed well in each decade over more than a century, as far back as we can get reliable return data for several markets.

Our analysis provides significant out-of-sample evidence across markets and asset classes beyond the substantial evidence already in the literature. Further, we find that a trend-following strategy has performed relatively similarly across a variety of economic environments, and provided significant diversification benefits to a traditional allocation. This consistent long-term evidence suggests that trends are pervasive features of global markets.

References
Asness, C. “Variables that Explain Stock Returns.” Ph.D. dissertation, University of Chicago, 1994. Asness, C., J. Liew and R.L. Stevens. “Parallels between the cross-sectional predictability of stock and country returns.” The Journal of Portfolio Management, Vol. 23, No. 3 (1997), pp. 79–87. Asness, C., T. Moskowitz and L.H. Pedersen. “Value and Momentum Everywhere.” The Journal of Finance,
Vol. 68, No. 3 (2013), pp. 929–985. Baltas, A.N. and R. Kosowski. “Momentum strategies in futures markets and trend-following funds.” Working paper, Imperial College Business School, 2013. – –. “Demystifying time-series momentum strategies: volatility estimators, trading rules and pairwise correlations.” Working paper, Imperial College Business School, 2015. Chabot, B., E. Ghysels and R.

Jagannathan. “Momentum Cycles and Limits to Arbitrage: Evidence from
Victorian England and Post-Depression U.S. Stock Markets.” Working paper, Yale University, 2009. Cutler, D.M., J.M. Poterba and L.H. Summers. “Speculative dynamics.” The Review of Economic Studies, Vol. 58, No. 3 (1991), pp. 529–546. Erb, C.B., and C.R. Harvey. “The tactical and strategic value of commodity futures.” Financial Analysts Journal,
Vol. 62, No. 2 (2006), pp. 69–97. Fung, W., and D.A. Hsieh. “Empirical Characteristics of Dynamic Trading Strategies: The Case of Hedge Funds.”
Review of Financial Studies, Vol. 10, No. 2 (1997), pp. 275-302. – –. “The Risk in Hedge Fund Strategies: Theory and Evidence From Trend Followers.” Review of Financial
Studies, Vol. 14, No. 2 (2001), pp. 313–341. Georgopoulou, A., and J.

Wang. “The Trend is Your Friend: Time-series Momentum Strategies across Equity and Commodity Markets.” Review of Finance, forthcoming, 2016. Goetzmann, W., R.G. Ibbotson and L. Peng. “A New Historical Database for the NYSE 1815 to 1925:
Performance and Predictability.” Working paper, Yale University, 2000. Gorton, G.B., F. Hayashi and K.G. Rouwenhorst. “The Fundamentals of Commodity Futures Returns.” Working paper, Yale University, 2008. Grant, J. The Great Metropolis, vol. II. Philadelphia, PA: E.L. Carey & A. Hart, 1838. Greyserman, A. and K. Kaminski. Trend Following with Managed Futures. Hoboken, NJ: Wiley , 2014. Hurst, B., Y.H. Ooi and L.H. Pedersen. “Demystifying Managed Futures.” Journal of Investment Management,
Vol. 11, No. 3 (2013), pp. 42-58.

Jegadeesh, Narasimhan, and Sheridan Titman, 1993, “Returns to Buying Winners and Selling Losers:
Implications for Stock Market Efficiency,” The Journal of Finance 48(1), 65–91. Jones, C.M. “A Century of Stock Market Liquidity and Trading Costs.” Working paper, Columbia Business
School, 2002. Levine, A. and L.H. Pedersen. “Which Trend is Your Friend?” Financial Analysts Journal, Vol. 72, No. 3 (2016), pp. 51-66.

Menkhoff, L., L. Sarno, M. Schmeling, and A. Schrimpf. “Currency momentum strategies,” Journal of Financial
Economics, Vol. 106, No. 3 (2012), pp. 620-684.
Moskowitz, T., Y.H. Ooi and L.H. Pedersen. “Time Series Momentum.” Journal of Financial Economics, Vol.
104, No. 2 (2012), pp. 228–250.
Rouwenhorst, K.G. “International Momentum Strategies,” The Journal of Finance, Vol. 53, No. 1 (1998), pp.
267–284.
Shleifer, A., and L.H. Summers. “The Noise Trader Approach to Finance,” Journal of Economic Perspectives,
Vol. 4, No. 2 (1990), pp. 19–33.
Silber, W.L. “Technical trading: when it works and when it doesn't.” The Journal of Derivatives, Vol. 1, No. 3
(1994), pp. 39-44.

Exhibit 1. Performance of Time Series Momentum, 1880-2016. This table shows the strategy’s annualized excess returns (i.e., returns in excess of the risk-free interest rate) before and after simulated transaction costs, and gross and net of hypothetical 2-and-20 fees. Gross of Fee, Gross of Fee, Net of 2/20 Fee, Realized Sharpe Ratio, Correlation Correlation to
Gross of Cost Net of Cost Net of Cost Volatility Net of Fees to U.S.

US 10-year Bond
Time Period
Excess Returns Excess Returns Excess Returns and Costs Equity Market Returns
Full Sample
Jan 1880-Dec 2016 18.0% 11.0% 7.3% 9.7% 0.76 -0.01 -0.03
By Decade
Jan 1880-Dec 1889 12.1% 5.2% 2.6% 9.5% 0.27 -0.11 -0.04
Jan 1890-Dec 1899 17.4% 10.0% 6.5% 8.9% 0.73 -0.02 -0.15
Jan 1900-Dec 1909 15.3% 6.0% 3.3% 9.5% 0.34 0.02 -0.35
Jan 1910-Dec 1919 12.5% 4.1% 1.6% 12.6% 0.13 0.12 -0.01
Jan 1920-Dec 1929 20.8% 13.3% 9.2% 8.5% 1.09 0.15 0.06
Jan 1930-Dec 1939 15.4% 9.8% 6.3% 8.6% 0.74 -0.11 0.20
Jan 1940-Dec 1949 23.8% 14.8% 10.4% 10.6% 0.99 0.33 0.31
Jan 1950-Dec 1959 26.7% 17.6% 13.1% 9.1% 1.45 0.23 -0.19
Jan 1960-Dec 1969 21.0% 9.5% 6.0% 10.9% 0.56 -0.09 -0.37
Jan 1970-Dec 1979 27.4% 20.5% 15.1% 8.9% 1.70 -0.24 -0.25
Jan 1980-Dec 1989 20.1% 13.3% 9.1% 9.4% 0.96 0.18 -0.16
Jan 1990-Dec 1999 16.8% 12.3% 8.3% 8.4% 0.98 0.01 0.21
Jan 2000-Dec 2009 11.6% 9.9% 6.3% 10.3% 0.61 -0.34 0.27
Jan 2010-Dec 2016 7.6% 6.2% 3.3% 8.1% 0.41 -0.15 0.28

Exhibit 2. Performance of Time Series Momentum by Signal. This table shows the annualized gross Sharpe Ratio (i.e., excess return before simulated transaction costs and fees divided by volatility) separately for each time series momentum signal based on the past 1-month, 3-month, and
12-month trend, respectively. Also, the table shows the performance when each of these signals is lagged by one month.

1 Month 1 Month 3 Month 3 Month 12 Month 12 Month
Time Period Strategy Strategy Strategy Strategy Strategy Strategy
(Lagged) (Lagged) (Lagged)
Full Sample
Jan 1880-Dec 2016 1.38 0.45 1.19 0.64 1.32 1.04
By Decade
Jan 1880-Dec 1889 1.02 -0.34 0.78 -0.23 1.03 0.89
Jan 1890-Dec 1899 1.32 0.34 0.91 0.25 1.35 0.83
Jan 1900-Dec 1909 0.87 0.35 1.20 0.65 1.52 1.52
Jan 1910-Dec 1919 0.80 0.01 0.63 0.39 0.99 0.83
Jan 1920-Dec 1929 1.75 0.56 1.23 0.51 1.77 1.27
Jan 1930-Dec 1939 1.19 0.27 1.21 0.29 1.09 0.70
Jan 1940-Dec 1949 2.16 1.09 1.65 1.29 1.54 1.27
Jan 1950-Dec 1959 2.48 1.48 1.95 1.38 1.55 1.27
Jan 1960-Dec 1969 1.81 0.31 1.31 0.68 1.01 0.42
Jan 1970-Dec 1979 2.24 0.82 2.13 1.34 1.91 1.66
Jan 1980-Dec 1989 1.77 0.40 1.09 0.50 1.46 1.07
Jan 1990-Dec 1999 1.13 0.49 1.52 0.75 1.38 1.20
Jan 2000-Dec 2009 0.70 0.38 0.67 0.66 1.10 0.86
Jan 2010-Dec 2016 0.06 0.13 0.30 0.33 0.73 0.70

Exhibit 3. Time Series Momentum Performance by Individual Asset: Full Sample
This figure shows the Sharpe Ratio of time series momentum (gross of fee, gross of cost) by asset, 1880-2016.

Exhibit 4. Time Series Momentum Sharpe Ratios for Individual Assets, Before 1985.
This figure shows the Sharpe Ratio of time series momentum (gross of fee, gross of cost) by asset, 1880-1984.
We only include assets that have at least 10 years of data before 1985. This evidence is out-of-sample relative to the study of Moskowitz, Ooi and Pedersen [2012].

Exhibit 5. Time Series Momentum “Smile.”
This figure shows the annual returns of time series momentum (gross of fee, net of cost) versus U.S. equity market returns, 1880-2016, as well as the fitted second order polynomial.
Exhibit 6. Time Series Momentum during the 10 Worst Drawdowns for 60/40.
This figure shows the returns of time series momentum (gross of fee, net of cost) and return of the portfolio that invests 60% in US stocks and 40% in US bonds over the 10 time periods that are selected as the largest drawdowns for the latter portfolio.

Exhibit 7. Combining 60/40 with an Allocation to Time Series Momentum. This table reports the historical performance characteristics of the 60/40 portfolio that invests 60% in US equities and 40% in US bonds. Also, the table reports the performance of a portfolio with 80% invested in the 60/40
portfolio (gross of fees and transaction costs) and 20% invested in the time series momentum strategy (net of fees and net of transaction costs), from January 1880 to December 2016. Annualized Excess of Cash Returns Annualized Vol Max Drawdown Sharpe Ratio
60/40 Portfolio 4.1% 10.7% -62.3% 0.39
80% 60/40 Portfolio, 20%
Time Series Momentum
Strategy 4.8% 8.7% -50.2% 0.55
Exhibit 8. The 10 Largest Drawdowns of Time Series Momentum, 1880-2016.

This table reports the 10 largest peak-to-trough drawdowns of the time series momentum strategy, calculated using gross of fee, net of cost returns.

Rank Start of Lowest End of Size of Excess Return Peak-to- Trough-toDrawdown Point of Drawdown Peak-to- During Peak-to- Trough Recovery
(Peak) Drawdown (Recovery) Trough Trough Length Length
(Trough) Drawdown Drawdown (Months) (Months)
1 Aug 1947 Dec 1948 Feb 1951 -24.7% -26.1% 16 26
2 Apr 1912 Jan 1913 Aug 1914 -22.8% -26.3% 9 19
3 Feb 1937 Jun 1940 Aug 1941 -21.2% -21.6% 40 14
4 Mar 1918 Feb 1919 Feb 1920 -20.4% -25.6% 11 12
5 Aug 1966 Dec 1966 Mar 1968 -17.7% -19.4% 4 15
6 Jun 1964 Aug 1965 Dec 1965 -17.2% -21.6% 14 4
7 Mar 2015 May 2016 N/A -16.1% -16.2% 14 N/A
8 Aug 1896 Jun 1897 Dec 1898 -15.0% -17.7% 10 18
9 Apr 1885 Jun 1885 Jul 1887 -14.4% -14.6% 2 25
10 Feb 1904 Jul 1904 Jun 1906 -14.1% -15.1% 5 23

Exhibit 9. Time Series Momentum Across Economic Regimes: Binary Indicators. This table shows the performance before fees and after simulated transaction costs. For each economic regime, we report the annualized excess return, its t-statistic, volatility, and Sharpe ratio. The regimes are “recession vs. boom” indicators as defined by NBER Business Cycle Dating Committee; “inflation: low vs. high” based on U.S. CPI from 1913 to 2016 and before 1913, defined as Watten and Pearson [1935] price index; “war vs. peace,” where war periods are World War 1, World War 2,
Vietnam War, and Korean War (wars with more than 1 million casualties with at least three nations at war) and peace are other time periods; “stock market: bull vs.

bear,” where bear markets are defined as periods where peak to trough drawdown of U. S. equity market is greater than 20% and bull market is all other times. In Panel A, we consider the contemporaneous effect – e.g., for “war” we compute the return during each recession month of war even if the war started mid-month. In Panel
B, we lag the indicator of the economic environment – e.g., for “war” we compute the return each month following a war month. Panel A: Time Series Momentum Returns by Contemporaneous Macro Indicators
Macro indicator Statistic Group 1 Group 2 Difference
Recession vs. Boom Excess return 10.4% 11.2% 0.8%
(t-statistic) (5.4) (10.7) (0.4)
Volatility 11.6% 10.5%
Sharpe ratio 0.90 1.07
% of occurrences 26% 74%
Inflation: Low vs.

High Excess return 10.5% 11.5% 1.0%
(t-statistic) (8.4) (8.4) (0.5)
Volatility 10.5% 11.2%
Sharpe ratio 1.01 1.03
% of occurrences 51% 49%
War vs. Peace Excess return 13.5% 10.2% -3.3%
(t-statistic) (6.7) (9.9) (-1.5)
Volatility 11.5% 10.6%
Sharpe ratio 1.17 0.97
% of occurrences 24% 76%
Stock Market: Bull vs. Bear Excess return 10.2% 15.5% 5.3%
(t-statistic) (10.4) (5.9) (1.9)
Volatility 10.6% 12.0%
Sharpe ratio 0.96 1.30
% of occurrences 85% 15%
Panel B: Time Series Momentum Returns by Lagged Macro Indicators
Macro indicator Statistic Group 1 Group 2 Difference
Recession vs. Boom Excess return 10.1% 11.4% 1.3%
(t-statistic) (5.1) (11.0) (0.6)
Volatility 11.9% 10.4%
Sharpe ratio 0.84 1.09
% of occurrences 26% 74%
Inflation: Low vs.

High Excess return 11.8% 10.2% -1.7%
(t-statistic) (9.7) (7.3) (-0.9)
Volatility 10.3% 11.4%
Sharpe ratio 1.15 0.90
% of occurrences 51% 49%
War vs. Peace Excess return 13.8% 10.1% -3.7%
(t-statistic) (6.8) (9.8) (-1.6)
Volatility 11.6% 10.5%
Sharpe ratio 1.19 0.96
% of occurrences 24% 76%
Stock Market: Bull vs. Bear Excess return 10.3% 14.8% 4.5%
(t-statistic) (10.6) (5.6) (1.6)
Volatility 10.6% 12.1%
Sharpe ratio 0.98 1.22
% of occurrences 85% 15%

Exhibit 10. Time Series Momentum Across Economic Regimes: Quintiles. This table shows the performance before fees and after simulated transaction costs. For each economic regime, we report the annualized excess return, its t-statistic, volatility, and Sharpe ratio. We consider the economic indicators: S&P volatility (estimated over the past 36 month), the 3-month change in the estimated volatility, the average absolute pairwise correlations across the markets, and the T-bill yield. For each indicator, we sort the data into quintiles, and report the contemporaneous time series momentum performance in Panel A. In Panel B we report the time series momentum performance in the following month (or, said differently, the economic indicator is lagged one month).

Panel A: Time Series Momentum Returns by Contemporaneous Macro Indicators
Macro indicator Statistic Quintile 1 Quintile 2 Quintile 3 Quintile 4 Quintile 5
S&P Volatility Level Excess return 6.9% 15.8% 15.9% 8.5% 8.0%
(Horizon: 36 Months) (t-statistic) (3.0) (7.7) (8.2) (4.2) (4.1)
Volatility 11.9% 10.8% 10.2% 10.6% 10.2%
Sharpe ratio 0.58 1.46 1.56 0.80 0.78
S&P Volatility Change Excess return 13.1% 10.6% 10.1% 10.6% 10.7%
(Horizon: 3 Months) (t-statistic) (6.9) (5.2) (5.3) (5.3) (4.3)
Volatility 9.9% 10.6% 10.0% 10.3% 13.0%
Sharpe ratio 1.32 1.00 1.01 1.02 0.83
Absolute Pairwise Excess return 17.1% 15.0% 8.6% 6.3% 8.0%
Correlation (t-statistic) (8.1) (7.4) (4.3) (3.4) (3.5)
Volatility 11.1% 10.6% 10.5% 9.6% 11.9%
Sharpe ratio 1.54 1.42 0.83 0.66 0.67
T-Bill Yields Excess return 12.2% 10.2% 7.5% 11.9% 13.2%
(t-statistic) (5.8) (4.9) (4.1) (5.8) (5.9)
Volatility 11.1% 10.9% 9.4% 10.8% 11.7%
Sharpe ratio 1.10 0.94 0.79 1.10 1.13
Panel B: Time Series Momentum Returns by Lagged Macro Indicators
Macro indicator Statistic Quintile 1 Quintile 2 Quintile 3 Quintile 4 Quintile 5
S&P Volatility Level Excess return 7.8% 15.9% 15.2% 6.4% 9.8%
(Horizon: 36 Months) (t-statistic) (3.4) (7.5) (7.7) (3.2) (5.3)
Volatility 12.0% 11.2% 10.3% 10.5% 9.7%
Sharpe ratio 0.65 1.43 1.47 0.61 1.00
S&P Volatility Change Excess return 14.1% 10.3% 7.9% 12.1% 10.6%
(Horizon: 3 Months) (t-statistic) (7.3) (5.1) (3.8) (5.8) (4.8)
Volatility 10.1% 10.6% 10.8% 10.9% 11.6%
Sharpe ratio 1.40 0.98 0.73 1.11 0.91
Absolute Pairwise Excess return 18.8% 14.1% 8.7% 7.3% 6.2%
Correlation (t-statistic) (8.4) (6.8) (4.9) (3.6) (3.0)
Volatility 11.7% 10.9% 9.4% 10.6% 11.0%
Sharpe ratio 1.61 1.29 0.93 0.69 0.57
T-Bill Yields Excess return 11.1% 11.8% 8.7% 10.3% 13.2%
(t-statistic) (5.5) (5.9) (4.4) (5.0) (5.9)
Volatility 10.7% 10.5% 10.4% 10.7% 11.7%
Sharpe ratio 1.04 1.12 0.84 0.96 1.13

Exhibit 11. Average Absolute Pairwise Asset Correlations.
This figure shows the absolute pairwise correlations across all assets available at each time, estimated over 36
months.

Appendix
Appendix A: Markets and Data Sources
We use historical returns data from 67 markets as seen in Exhibit A1. Below we list our data sources. Equity Indices. The universe of equity index futures consists of the following 11 developed equity markets: SPI
200 (Australia), S&P/TSE 60 (Canada), CAC 40 (France), DAX (Germany), FTSE/MIB (Italy), TOPIX (Japan),
AEX (Netherlands), IBEX 35 (Spain), FTSE 100 (U.K.), Russell 2000 (U.S.) and S&P 500 (U.S). Futures returns are obtained from Datastream and Bloomberg. We use MSCI country level index returns and returns from
Ibbotson, Global Financial Data (GFD) and the Yale School of Management prior to the availability of futures returns. Bond Indices.

The universe of bond index futures consists of the following 15 developed bond markets: Australia
3-year bond, Australia 10-year bond, Euro Schatz (2-year), Euro Bobl (5-year), Euro Bund (10-year), Euro Buxl
(30-year), Canada 10-year bond, Japan 10-year bond (TSE), Long Gilt, U.S. 2-year Note, Italian 10-year bond,
French 10-year bond, U.S. 5-year note, U.S. 10-year note and U.S. long bond. Futures returns are obtained from
Morgan Markets and Bloomberg. We use country level cash bond returns from Datastream, Ibbotson and Global
Financial Data (GFD) prior to the availability of futures returns. We scale monthly returns from GFD and Ibbotson to a constant duration of 4 years, assuming a duration of 2 years for the U.S. 2-year note, 4 years for the U.S.

5year note and German REX Index, 20 years for the U.S. long bond and 7 years for all other bonds. Currencies. The universe of currency forwards covers the following 10 currencies: Australian dollar, Canadian dollar, German mark spliced with the euro, Japanese yen, New Zealand dollar, Norwegian krone, Swedish krona,
Swiss franc, British pound and U.S. dollar. We use spot and forward interest rates from Citigroup to calculate currency returns going back to 1989 for all the currencies except for CAD and NZD, which go back to 1992 and
1996. Prior to that, we use spot exchange rates from Datastream and LIBOR short rates from Bloomberg to calculate returns. Commodities.

We use a data set of 29 different commodity futures that is significantly longer than what has been previously used in the literature. Where available, we use futures price data from Bloomberg. For periods before
Bloomberg data is available, we use futures prices from Commodity Systems Inc. and a data set constructed from the historical records of the Chicago Board of Trade. In particular, the data from 1877 to 1951 was manually transcribed from the Annual Report of the Trade and Commerce of the Chicago Board of Trade (CBOT). To ensure accuracy, two independent data vendors transcribed the same data set, and their transcriptions were crossverified to be mutually consistent.

We note that, opening and closing prices were not recorded in the early part of the sample, so we use the average of high and low prices before closing prices are available. Finally, the roll schedule is seeks to hold one the most liquid futures contracts across maturities. For example, each month in the hand collected data, we hold the nearest of the contracts whose delivery month is at least two months away.

Exhibit A1: Data sources by market and time period.

Appendix B: Simulation of Fees and Transaction Costs
In order to calculate net-of-fee returns for the time series momentum strategy, we subtracted a 2% annual management fee and a 20% performance fee from the gross-of-fee returns to the strategy. The performance fee is calculated and accrued on a monthly basis, but is subject to an annual high-water mark. In other words, a performance fee is subtracted from the gross returns in a given year only if the returns in the fund are large enough that the fund’s NAV at the end of the year exceeds every previous end of year NAV. The transactions costs used to simulate the net returns of the strategy are given in Exhibit B1.

These are based on proprietary estimates of average transaction costs for each of the four asset classes, including market impact and commissions, made in 2012. Further, the transaction costs are assumed to be twice as high from 1993 to 2002 and six times as high from 1880–1992, based on Jones [2002]. We note that the transaction costs are estimated with a significant amount of uncertainty and do not include potential other costs such as the costs of rolling futures contracts. Exhibit B1. Simulated transaction costs. This table shows the assumed transaction costs for the time period 2003-2016. The transaction costs are assumed to be twice as high from 1993 to 2002 and six times as high from 1880–1992, based on Jones [2002].

Asset Class Time Period One-Way Transaction Costs
(as a % of notional traded)
1880-1992 0.34%
Equities 1993-2002 0.11%
2003-2016 0.06%
1880-1992 0.06%
Bonds 1993-2002 0.02%
2003-2016 0.01%
1880-1992 0.58%
Commodities 1993-2002 0.19%
2003-2016 0.10%
1880-1992 0.18%
Currencies 1993-2002 0.06%
2003-2016 0.03%
