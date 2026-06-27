---
family: B
source: macro-eco nowcasting business cycle turning points
doc_type: pdf
reliability: 95
tickers: []
ingested: 2026-06-27
---

Working Paper Series
Andres Azqueta-Gavaldon, Nowcasting business cycle
Dominik Hirschbühl, Luca Onorante, turning points with stock networks
Lorena Saiz and machine learning
No 2494 / November 2020
Disclaimer: This paper should not be reported as representing the views of the European Central Bank
(ECB). The views expressed are those of the authors and do not necessarily reflect those of the ECB.

Abstract
We propose a granular framework that makes use of advanced statistical methods to approximate developments in economy-wide expected corporate earnings. In particular, we evaluate the dynamic network structure of stock returns in the United States as a proxy for the transmission of shocks through the economy and identify node positions (firms) whose connectedness provides a signal for economic growth. The nowcasting exercise, with both the in-sample and the out-of-sample consistent feature selection, highlights which firms are contemporaneously exposed to aggregate downturns and provides a more complete narrative than is usually provided by more aggregate data.

The two-state model for predicting periods of negative growth can remarkably well predict future states by using information derivedfromthenode-positionsofmanufacturing,transportationandfinancial(particularly insurance) firms. The three-states model, which identifies high, low and negative growth, successfully predicts economic regimes by making use of information from the financial, insurance, and retail sectors. JEL Classification: C45; C51; D85; E32; N1. Keywords: real-time; turning point prediction; Granger-causality networks; early warning signal. ECB Working Paper Series No 2494 / November 2020 1

. Non-technical summary
A real-time identification of recessions and economic “regimes” (i.e. phases of the business cycle) proves difficult, but it is of great importance for policy-makers. We propose a novel approach for identifying changes in economic regimes in real time. Our approach utilises various measures of connectedness in a stock returns network as a proxy for the transmission of shocks through the economy. We show that the dynamic network structure contains forward-looking cyclical information and is a good predictor of booms and recessions. We emphasise the role of granular, firm-level information, and its connectedness to unveil aggregate shocks.

When consumer and business spending softens in some part of the economy, corporate earnings start to decline and businesses seek ways to cut costs. They might downsize their workforce, put a freeze on hiring and delay investments. As these factors become more widespread, unemployment rises, aggregate wages fall and demand weakens further, tipping the economy into recession. Once demand for goods and services increases again, earnings rise supporting higher stock prices. Although every recession is different,thereisaclearlinkbetweenthestateoftheeconomy,corporateearningsandstock price developments. Our dynamic stock network captures the connectedness of shocks to expected corporate earnings and hence allows us to detect the propagation of shocks within the economic system.

The main findings can be summarised as follows. The baseline binary state model can predictupcomingrecessionsbyusinginformationfromthenode-positionsofmanufacturing, transportation and financial, particularly insurance firms. The ternary state model (featuring high, low growth, and recessions) successfully predicts economic regimes highlighting the role of information stemming from the financial, the insurance, and the retail sectors. Looking at the economic system as a whole, we highlight that during an expansion adverse shocks to firms are mostly idiosyncratic, while during contractions shocks become more widespread resulting in higher connectedness in certain parts of the network.

Measures of centrality efficiently summarise economy-wide developments and allow us to monitor the state of the economy in real time. ECB Working Paper Series No 2494 / November 2020 2

1 Introduction
A real-time identification of recessions and economic “regimes” (i.e. phases of the businesscycle) isof greatimportancefor policy-makers. Wepropose anovelapproach for identifying changes in economic regimes in real time. Our approach utilises measures of connectedness in a stock network as a proxy for the transmission of shocks through the economy and, hence, for widespread developments in corporate earnings. We show that the dynamic network structure contains forward-looking cyclical information, making it an optimal predictor of booms and recessions. The identification of turning points or different phases of the business cycle in real time has proven rather difficult, despite a large literature on the subject and an ever increasing number of leading indicators.

In this respect, the consensus in the literature is that the set of relevant indicators for predicting shifts in business cycle phases (e.g. recessions) changes over time. Therefore, indicators that are useful for predicting one recession do not necessarily serve to predict other recessions as “every cycle is different”. A general problem of forecasting economic regimes as shown by Ng
(2014) is that only a few indicators are actually useful and the effectiveness of these indicators varies according to the forecast horizon. For example, financial variables
(e.g.

term and corporate spreads) are appropriate for forecasting 6 to 12 months ahead in view of their forward-looking nature.1
One important reason for the delay in identifying shifts in business cycle phases is that the overall economy is normally reduced to a summation of its components and micro-level shocks are therefore assumed to offset each other at the aggregate level. By contrast, the approach adopted in this work emphasises the importance of granularity and the role of economy-wide return connectedness. When consumer and business spending softens in some parts of the economy, corporate earnings start to decline and businesses seek ways to cut costs. They might downsize their workforce, put a freeze on hiring and delay investments.

As this situation becomes more widespread, unemployment rises, aggregate wages fall and demand weakens further,
1Inournetworkapproach,wefocusonnowcasting. Investigatingtheforward-lookinginformationcontent in the derived network measures is left for future work. ECB Working Paper Series No 2494 / November 2020 3

tipping the economy into recession. Although every recession is different, there is a clear link between the state of the economy, corporate earnings and stock price developments. Once demand for goods and services increases again, earnings rise supporting higher stock prices. Translating the company information contained in stock returns into a dynamic stock network allows us to proxy widespread developments in actual and expected corporate earnings and, hence, shock propagation within the economic system. Considering that changes in stock market returns can reflect both idiosyncratic and economy-wide shocks, we calculate pairwise Granger causality within companies’ stock returns.

A relation at a period t only exists if the daily returns of a company over a 12-month horizon provide statistically significant information for predicting the returns of another company and vice versa. During an expansion adverse shocks to firms are mostly idiosyncratic, while during contractions shocks become more widespread which results in higher connectedness in the network. We can monitor economy-wide developments by calculating measures of centrality that reflect increasing co-movement in the economy, thereby creating a “fat” data-set of roughly 5,002 time-series. Given that pure financial shocks are predominant in the network, we need to identify the characteristics of the dynamic network that are more likely to reflect economy-wide propagation leading to booms or recessions.

The work that is closest to ours is Heiberger (2018),2 but we extend it in several ways. First, we construct the network on the basis of pairwise Granger-causalities rather than correlations. Limiting links to statistically relevant causality focuses on relationships that are economically relevant for shock transmission in the network, while reducing noise. The point is to identify the stocks/nodes that react earlier to shocks and play a role in their transmission (i.e. they are systemically relevant). We show that relevant economy-wide developments are only imperfectly reflected in the aggregate data, while firm-specific network characteristics are important early indicators of the state of the US economy.

Second, we innovate by letting different algorithms such as support vector machines (SVM), naive Bayes (NB) and logistic
2 Theauthorcreatesadynamiccorrelation-basednetworkforstockmarketreturnsina12-monthrolling window. it assumes a critical threshold of correlation of 0.7. The author’s approach requires an optimal number of network features of around 2,200. ECB Working Paper Series No 2494 / November 2020 4

regression (LR) compete. We analyse two models. The first tries to identify two economic regimes: “recession” (defined as negative growth in the quarter) and its complement. In the second model, we try to perform the more challenging task of distinguishing between three regimes: “negative growth” (defined as negative growth in the quarter), “low growth” (defined as positive, but below high growth) and “high growth” (defined as annualised growth higher than 3% in the quarter). Our findings suggest that our network approach can help to detect changes in economic regimes in real-time, giving policy-makers a tool to anticipate slowdowns and take measures against them.

The main findings can be summarised as follows: (i) Applying recursive feature elimination (RFE) on the entire sample, we are able to determine ex-post which firms were exposed to economy-wide earnings shocks that turned into aggregate fluctuations, while remaining resilient to others. Looking at the sectors where these firms operate, a more complete narrative can be derived than is usually derived from more aggregate data. The two-state model for predicting periods of negative growth can remarkably well predict future states by using information from the node-positions of manufacturing, transportation and financial, particularly insurance firms.

The ternary state modelsuccessfullypredictseconomicregimesbymakinguseofinformationfromafew node-positions from the financial and insurance sectors, as well as the retail sector. (ii) Using features (variables) that are selected to be optimal until the fourth quarter of 2006 (i.e. excluding the out-of-sample period), we validate our models in terms of true out-of-sample performance to verify that the in-sample results are not solely due to favorable feature selection. Unsurprisingly, the number of selected features is higher than in the in-sample exercise.

While the predictions of the binary state model are weak, the ternary state captures the turning point of the great recession and performs overall well, while creating some false positives in the negative growth state in moments of weak growth momentum. The rest of this paper proceeds as follows. Section 2 reviews differing approaches and sets them into the context of this study. Section 3 discusses the methodology of our approach. Section 4 illustrates the findings while Section 5 concludes. ECB Working Paper Series No 2494 / November 2020 5

2 Related literature
A large amount of literature has investigated models and economic and financial indicators that could be useful to predict or anticipate an economic downturn. The real-time predictive power of such models, however, has often proved unsatisfactory. In conventional frameworks, the inclusion of selected financial indicators has partially captured the effect of the financial cycle on recessions. The high costs that are associated with systemic risk and financial crises led to an extensive literature investigating the linkages between the financial sector and crises. Early warning models estimated with conventional techniques include Alessi and Detken (2011), Rose and Spiegel
(2012), Gourinchas and Obstfeld (2012), Duca and Peltonen (2013) or Drehmann and Juselius (2014).

This macro approach (based on macro aggregates) is partially successful, andhasbeenabletoidentifysomedeterminantsoffinancialcrises(e.g. the credit to GDP ratio). However, the problem remains that variables that have been found to be important, such as credit, are usually in the form of aggregates, which, by their nature, miss the tails and off-mean events that may trigger a recession. In an attempt to overcome this, Adrian et al. (2019) estimate the predictive US
GDP growth conditional distribution based on a synthetic index of financial conditions. This index aggregates variables that cover financial risk, leverage and credit quality. The analysis finds that the lower quantiles of GDP growth are more sensitive tofinancial conditions thanupper quantiles.

This findingsuggests an asymmetricand non-linear relationship between financial and real variables. Plagborg-Møller et al. (2020) find that financial variables have very limited predictive power for the distribution of GDP growth at short horizons, especially, but not limited to, the tail risk. This is due to the fact that moments other than the mean are estimated imprecisely and information in monthly financial variables is highly correlated. However, there are still several shortcomings of macro-based analysis. First, using aggregate data averages out shocks. That is, aggregation in the data “averages out”
micro shocks because interactions are neglected in favour of averaging.

Therefore, a macro approach (using aggregate data) is only suitable for identifying aggregate
ECB Working Paper Series No 2494 / November 2020 6

shocks that result from macroeconomic policies. To the extent that systemic risk is determined by the complex interactions of micro shocks, macro aggregates would not be able to account for network effects. Second, aggregate data are usually not available on a timely basis. In the United States, the Bureau of Economic Analysis
(BEA) releases the first estimate of the gross domestic product one month after the end of the reference quarter. A second estimate is published two months after the end of the reference quarter. And finally, a third estimate is released three months after the end of the reference quarter.

A breakdown of GDP by industry is available later, with an average delay of 120 days.3 Third, there are substantial non-linearities that standard regression models struggle to capture. Attempts to identify non-linearities ineconomicprocessesmostlyinvolveMarkovswitchingmodelsandmultipleeconomic regimes (for instance, Chauvet and Hamilton (2006) and Camacho et al. (2018)), or the estimation of probit and logit regressions. Recently, researchers have started to explore unconventional “big data” and/or techniques such as machine learning methods to forecast the business cycle, obtainingsomepromisingresults.

Forinstance, Qi(2001)predictsUSrecessionswithneural network models and a set of leading financial and economic indicators, and Giusto and Piger (2017) use Learning Vector Quantization (LVQ) to identify US business cycle turning points in real time. In this paper, we follow this strand of research and propose to evaluate network information generated from stock returns to proxy the propagation of economic shocks that result in recessions. For example, Gabaix (2011) shows that idiosyncratic firmlevel shocks can explain a large part of aggregate movements and provide a microfoundation for aggregate shocks. In particular, the idiosyncratic movements of the largest 100 firms in the United States appear to explain about one-third of variations in output growth. Acemoglu et al.

(2012) argue that in the presence of intersectoral input and output linkages microeconomic idiosyncratic shocks may lead to aggregate fluctuations. Næs et al. (2011) find that the liquidity in stock markets dries up prior to a crisis in the real economy while Li (2017) has shown that micro uncertainty (as
3 See the official release schedule published by the BEA on https://www.bea.gov/news/schedule
ECB Working Paper Series No 2494 / November 2020 7

measured by the idiosyncratic component in stock prices), translates into macro uncertainty via credit frictions in line with Bernanke et al. (1999). Ferreira (2018) shows that financial skewness, measured by comparing cross-sectional upside and downside risks of the distribution of stock market returns of financial firms, is a powerful predictor of business cycle fluctuations. Adam and Merkel (2019) present a model of the business cycle with extrapolative belief formation in which price effects of technology shocks are amplified such that large and persistent boom and bust cycles occur as observed in stock prices.

Nonetheless, there are two main challenges when incorporating the information provided by a network into fore- and nowcasting models: i) how to accommodate a network structure in an econometric framework (i.e. selection of informative features of the nodes in the network); and ii) whether and how to deal with the curse of dimensionality and select what is relevant. Given that networks usually produce a large amount of information (e.g. complex interactions between the groups that form the network), standard econometric models would not be sufficient for this task
(for example, our baseline specification is described by approximately 5,002 timeseries), and would, therefore, go beyond what macroeconometricians define as big data (see Giannone et al. (2018)).

To deal with this “curse of dimensionality”, we use machine learning techniques that perform variable selection, in particular RFE. In addition, to evaluate the remaining information we use competing machine learning methods: support vector machines, naive Bayes and a benchmark logistic regression. We build our network on financial data. More precisely, we use stock returns of listed companies in the Standard and Poor’s (S&P) 500 index. Financial data have the advantage of being non-proprietary and available in real time. From an economist’s point of view, there are two main reasons why quotations on financial markets can help to explain the business cycle.

First, financial markets process information efficiently, and quotations may be seen as informative summary statistics about a variety of firm characteristics such as the current status of company fundamentals and future expected performance as judged by the markets. Second, financial markets may additionally be the cause of sudden stops in the economy by turning
ECB Working Paper Series No 2494 / November 2020 8

small, idiosyncratic shocks into big aggregate shocks. Moreover, the presence of a representative sample of insurers and banks covers financial and credit links. Most importantly, stock prices are not subject to meaningful errors or revisions, which makes them particularly useful for nowcasting and forecasting. Notably, we recognise the difficulty of being robust to the “every cycle is different”
criticism. To achieve as much robustness as possible across different cycles, we exploit differenttypesofinformation. Wecomputeournetworksusingrolling12-monthswindows for each quarter ending on first working day of the second month in the quarter. Using those networks, we calculate node and aggregate network measures.

Finally, we obtain for each measure in each network one metric that we combine over time to obtain one time-series. We combine the time-series for all measures in a matrix. Finally, weletmachinelearningtechniquesdiscriminatebetweenusefulinformationandnoise. 3 Data and methodology
In this section we explain how we can model the relationships among companies using network theory. A network represents pair-wise relationships between nodes (firms in our case). Depending on the different attributes and relationships within the network, it will tell us relevant aggregate and sector-specific information about the way companies interact in the economy over time. Thus, representing the economy as a network has several potential advantages over looking at aggregate data (i.e.

overall stock market indices). We can use a wide range of information embedded in the network, such as the key firm or sector in the economy, and, more importantly, we can account for non-linearities in the relationship between economic players and the economic cycle. The exact procedure is summarised in the following steps:
Steps of the methodology
1. We have 500 series of daily returns data for the period from the first quarter of
1980 to the first quarter of 2019. 2. For each quarter:
ECB Working Paper Series No 2494 / November 2020 9

(a) For each possible pair-wise relationship between stock returns: i. Pick two firms’ daily returns series over a 12-month (rolling) window ending on the first working day of the second month in the quarter (e.g. 1 February for the first quarter of the year). ii. Test Granger causality of the two series using an heteroscedasticity and autocorrelation consistent (HAC) regression and 1% significance level. iii. If a Granger-causal relationship fill the network’s adjacency matrix
[500x(500-1)] with a 1 at the respective position, if not fill a 0. (b) From the first quarter of 1982 to the first quarter 2019, we calculate the proposed network measures and combine them along the time dimension to track the evolution of these measures over time.

In the feature matrix we consider solely the contemporary observation, hence we do not account for lagged values. We discard series that show too little variation over time. 3. We standardise all features to have a zero mean and a standard deviation of 1. 4. We use RFE in-sample to find contemporary highly correlated network metrics and choose the combination that performs best assuming k-fold cross-validation withk=54 ifwetreattheentiredataasin-sampleandk=3incaseweconsideran out-of-sample period. This unveils a reduced amount of features that have been independently highly correlated with GDP growth rates in different sub-periods in the past. 5. We train the logistic, SVM and naive Bayes classifiers on ranges of GDP growth rates making use of the selected features. 6.

We use the classification to nowcast economic “regimes” using stock network data in the selected period. 3.1 Data
Webuildourexplanatoryvariablesusingthedailystockreturnindex(whichaccounts for dividends and reinvestment within the underlying company). We obtain the data
4 3 in case of the ternary state model. ECB Working Paper Series No 2494 / November 2020 10

from Datastream and include all companies listed in the S&P 500 in the third quarter of 2018. The complete list of companies with identifiers can be found in Table A.3.3
in the Appendix. Table 1 illustrates the sectoral composition of the companies in the selected sample of firms as in the third quarter of 2018.5 As we can see, out of the
500 companies in the sample, the biggest share comprises manufacturing companies
(191), the second biggest share comprise financial companies (97) and transportation and services companies are tied for the third largest share (both with 71 companies). Note that we obtain sector-specific information using the Standard Industrial Classification (SIC).6
Table 1 Sectoral composition of the listed companies in the S&P 500 index
Sector #Nr.

of companies
Primary and construction 24
Manufacturing 191
Transportation 71
Wholesale 11
Retail 35
Finance 97
Services 71
Total 500
Notes: The table displays the sectoral composition of the S&P 500 index according to the Standard Industrial
ClassificationasdescribedinFootnote6. The total time span is from 2 January 1980 to 31 March 2019. Following the standard procedure in the literature, if there are no observations for the return of a given company (e.g. a company did not exist in the 1980s) information about the company is retained, but as we will see later on, no causality is assumed.

Using the constituents as at the third quarter of 2018 allows us to ignore changing compositions, but requires us to acknowledge that the network is imbalanced in the 1980s as it is gradually being compiled (see Figure A.16 in the Appendix). We obtained stock returns for each company i and time t by computing the difference in the logarithm of the return index at t and t−1: r = log(RI )−log(RI ). it it it−1
5 The choice constitutes a trade-off between keeping the number of companies limited, on the one hand, andfocusingonfirmsthatareimportantatthepresenttime,ontheotherhand. Thisresultsinimbalanced data as companies that were included in the third quarter of 2018 might not have existed in the 1980s.

6 The sectors are: Primary and construction (0100-1799), manufacturing (2999-3999), wholesale (50005199),transportation,electricityandgas(4000-4999),retail(5200-5999),financial,insuranceandreal-estate
(6000-6799),andservices(7000-8999). Theclassificationweproposecanbeappliedinamoregranularway. This information is solely used in the statistical review of features. ECB Working Paper Series No 2494 / November 2020 11

3.2 Pair-wise Granger-causality network
In order to build networks using firm stock returns, we compute pairwise Granger causality tests among each of the companies. To illustrate how we construct the
Granger causality network, consider Figure 1 which shows how a network can represent the interactions of three different companies. It is assumed that the returns of each company are available as a time series (top panel). In the left panel, the returns of companies B and C co-move whereas neither of them co-move with the returns of company A. These relationships are displayed as a network by connecting the nodes of only company B and company C. Moreover, these connections are bi-directional, in the sense that company B’s returns cause company C’s and vice versa.

In the third panel, however, we see that company A’s returns causes company B’s returns, since they move earlier in the same direction, but the reverse is not true (i.e. company B’s returns do not affect company A’s returns). For this reason, as we will see later on, we will have asymmetric relationships among companies. Figure 1 Construction of a Granger causality network
A
B
C
A A A A
B C B C B C B C
Notes: ThegraphillustrateshowtheGrangercausalitystocknetworkisconstructed. IfreturnsofcompanyBhelp toforecastreturnsofcompanyC,andviceversathenabi-directionaledgeiscreatedbetweenthetwocompanies. If returnsofcompanyAGranger-causereturnsofcompanyB,butnotviceversaaone-directionaledgeisassumed.

To account for causal interactions between stock returns rather than simply comovements or correlation, we make use of Granger-causality networks. GrangerECB Working Paper Series No 2494 / November 2020 12

causality networks have gained prominence by outperforming other approaches in displaying an extremely volatile degree of connectedness between financial institutions in times of financial crisis (see Billio et al. (2012)).7 Moreover, by applying them to a large and representative set of companies in the economy, it is also possible to capture patterns of economic developments over the business cycle. In order to calculate the Granger-causality networks, we follow Granger (1969),
Granger(1979)andBillioetal.(2012)andestimatelinearGranger-causalitynetworks on stock return indexes over rolling windows with a 12 month horizon.

We do so in two steps: first, we estimate bivariate vector autoregressions (VAR) using the
Bayesian Information Criterion (BIC) to specify the lags to be chosen.8 Second, we compute pairwise Granger-causality tests between the stock returns corrected for heteroscedasticity and autocorrelation (HAC). If the hypothesis of no causality is rejected, we assume a link between both stocks in the network. For both steps, we consider a significance level of 1% and a rolling window size of 12 months, as those parameters constitute a good choice for reflecting more persistent shocks. For instance, a 12-month rolling window is not solely focused on the short term, but also on somewhat more persistent shocks, which will be discussed in the next section.

Specifically, we represent each network in each periodtvia an adjacency matrix A(t): ij

 1 if i Granger causes j
A(t) = (1)
ij
 0 otherwise where we impose A(t) ≡ 0. It is worth noting that the adjacency matrix, unlike corii relation matrices as in Heiberger (2018), is generally not symmetric, as variable i can
Granger-cause j without the opposite being true. 7 In many applications, Granger-causality networks outperform networks based on dynamic Bayesian inference or simple correlation. In particular, if the data are not short they outperform dynamic Bayesian networks as shown by Zou and Feng (2009). In contrast to Billio et al. (2012), we apply heteroscedasticity and autocorrelation corrected Granger causality tests.

8 Assuming an informationally efficient financial market, short-term asset price changes should not be relatedtootherlaggedvariablesandnoreturnserieswouldbeexpectedtoGranger-causeanother. However, the presence of value of risk constraints, costs of gathering and processing information, and institutional restrictions creates Granger causalities among price changes in financial assets over time. ECB Working Paper Series No 2494 / November 2020 13

3.3 Network topology
Nonetheless, there are many other rich attributes that we can extract from a network beyond how compact or loose it is (as displayed in Figure 3). In this section we describe aggregate and firm/sector-specific network measures that we use throughout the analysis. We will rely on a number of centrality measures, which aim to identify the most important vertices within a network. • Dynamic causality index (economy and sectors)
N N
1 (cid:88)(cid:88)
DCI = A (2)
ij
N(N −1)
i(cid:54)=j j(cid:54)=i
The dynamic causality index (DCI) is described by the number of causal relationships over a given period divided by the number of total possible causal relationships.

The DCI describes the total number of Granger-causal relationshipsinthesystemandhenceisameasureofoverallconnectedness. Weconsider the DCI of the whole network and of sector-specific sub-networks. • Firm-specific or node-specific measures
In addition, we calculate various measures of node-level centrality which are illustrated in Figure 2. Measures of centrality attempt to identify the most important vertices within a network, e.g. the most influential firms or sectors. As we will see, there are many different ways of doing so, such as using the number of overall connections, connections within influential groups or flow across the network. In our set up, we consider five broad categories (and many more subcategories) of centrality which may characterise a network:
1. Degree centrality.

Degreecentralityisabasicmetricofconnectednesswhich measures the exposure of a company to the entire economy. More formally, it is the fraction of statistically significant Granger-causality relationships
ECB Working Paper Series No 2494 / November 2020 14

Figure 2 Actual network and node-level measures of centrality
Network In-degree Out-degree Degree Betweenness
A C C C C
B B A
C B A
D B D D D B A E
E D A E E E
Authorities In-closeness Out-closeness Pagerank Hubs
B C C C C
C B E A B A
B D
D A E D A E D A E B D E
Notes: Thegraphillustratesthesamenetworkatasingleperiodtwithnodesorderedandpicturedaccordingto differentnetworkmeasures. Highernodesareassignedhighervalues. among all N(N-1) pairs of N companies:
N
1 (cid:88)(cid:88)
DGC = (j → i). (3)
i
N(N −1)
i=1 j(cid:54)=i
Subcategories of degree centrality include the in-degree and out-degree measures. These measures account for all in-going and out-going relationships respectively.

A high in-degree measure identifies a receiver of shocks whereas a high out-degree connectedness identifies those nodes that are either originators of shocks or are exposed earlier to shocks in the network. 2. Closeness centrality. Closeness centrality defines node centrality in terms of the shortest paths. The distance between nodes i and j is given by the number of edges in the shortest path connecting them. A central node is therefore close to all other nodes in the network in terms of the average distance between this node and all others. Nodes with a high closeness reach the rest of the network in just a few steps and are able to quickly spreadshocksthroughthenetwork. Sinceournetworkisdirected(i.e.

there areGranger-causalitydirectionsamongfirms), itisbettertodistinguishbeECB Working Paper Series No 2494 / November 2020 15

tween in-closeness and out-closeness centrality. In-closeness centrality measures the degree to which a node can be easily reached from other nodes
(i.e. using the shortest path). Out-closeness centrality measures the degree to which a node can easily reach other nodes. 3. Betweenness centrality. Betweenness centrality is a measure related to closeness centrality since it is also based on shortest paths. Nonetheless, betweennes centrality does not require the network to be fully connected but can be calculated over multiple unconnected components (groups of nodes that are all connected to each other). (cid:88) σ (i)
j,k
B = (4)
i
σ
j,k i(cid:54)=j(cid:54)=k where σ is the path between j and k, and σ (i) is the number of paths a j,k j,k node i lies on.

Firms with high betweenness centrality serve as a bridge to otherwise weakly connected nodes, and have a high influence over the flow and contagion of shocks across parts of the network (e.g. between different sectors). An example of firms that serve as bridges is banks or financial institutions. They are connected to different firms in the economy as they provide them with credit and therefore can easily spread negative shocks throughout the whole economy. 4. PageRank centrality. PageRank is another centrality measure developed by
Google search in order to rank web pages according to how influential they are. PageRank works by counting the number and quality of links to a page to determine its importance.

It does so by representing the network as a
Markov chain in which each node is a state. The adjacency matrix can be transformed such that its elements represent the probability of transition between a pair of nodes. This measure computes the probability of arriving at the node i after a large number of steps following a random walk navigation through the network. Therefore, nodes with a higher probability are more central. ECB Working Paper Series No 2494 / November 2020 16

5. Hubs and authorities centrality. Hubs and authorities centrality are measures that give high scores to nodes which are so-called ”hubs” or ”authorities”. A hub node is one that points to many authority nodes, and an authority node is one that is pointed to by many hub nodes.9
3.4 Mapping stock networks to the business cycle
Figure 3 shows the average structure of the stock network during periods of recession and non-recession as defined by the US National Bureau of Economic Research
(NBER). The recession period chart displays all relationships that hold true in at least five of the nine NBER recession periods, while the non-recession period chart displays all other periods.

It appears that the network displays a high degree of connectedness during economic contractions, while during expansions shocks and, hence, stock returns behave more idiosyncratically, leading to lower connectedness. This information is summarised in the histogram in Figure 4.

Figure 3 Stylised network during phases of the business cycle
NBER Recession Periods NBER Non-Recession Periods lll l l l l l l l l l l l l l l l l l l l l l ll l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l lll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l ll l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l lll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l ll l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l l
Manufacturing Manufacturing
Primary & Construction Retail Services Primary & Construction Retail Services
Finance, Insurance and Real Estate Wholesale Transportation Finance, Insurance and Real Estate Wholesale Transportation
Notes: The figures display averaged quarterly stock networks of the S&P 500 based on pairwise Granger causal relationships from 2000:Q1 to 2019:Q1 on a 12 month rolling window bandwidth and a 5% significance level.

68
non-recessionperiodsand9recessionperiods. Thethresholdfortheaveragingis50%causalitiesperrelationforthe non-recession and the recession periods. This means that at connection holds at least in 5 out of 9 periods for the
NBERrecessioncase. Asthenetworkforthenon-recessionperiodswoulddisplaynoconnectednessatathresholdof
34outof68periods,wecanlowerthethresholdto7relationsper68periods. There is evidence that the financial system has increased in size and complex9 The easiest way to understand this is by using the example of building a network of journal articles usingcitations. Anarticlethatisreferencedbymanyotherarticleshasahighauthorityscore,andanarticle that cites many authority articles has a high hub score. ECB Working Paper Series No 2494 / November 2020 17

ity and its potential for causing economic disruption has correspondingly increased
(see, for example Zingales (2015)). The strong decoupling between money and credit aggregates shows that the leverage of the financial sector has increased strongly in recent decades. The transformations in financial intermediation are poised to have far-reaching implications for real-financial interactions and ultimately for business cycle dynamics. Not only has the size of the financial sector been steadily increasing in comparison with the size of the real economy; but the influence of the sector has also become proportionally greater as the result of increasing interdependence between financial and non-financial firms.

From the perspective of systemic risk, the financial sector can be thought of as a network of connected institutions that may benefit from having commercial relationships with each other but that can also translate micro shocks (e.g. firm-specific shocks) into systemic shock and cause financial crises. Figure 4 Normalised stable node-relations during phases of the business cycle
104 NBER Recession 105 Non-Recession
4 2
1.8
3.5
1.6
1.4
2.5
1.2
2 1
0.8
1.5
0.6
0.4
0.5
0.2
0 0
0 0.2 0.4 0.6 0.8 0 0.2 0.4 0.6 0.8
Notes: Thegraphillustratesnormalisedquarterlyconnectednessfromthefirstquarterof2000tothefirstquarterof
2019ona12-monthrollingwindowbandwidthwitha5%significancelevel.

ConnectednessinspecificnodesinNBER
recessionperiodsaremorepersistentthaninnon-recessionperiodswhereconnectednessmightbemoreidiosyncratic. Ahistogramusingdatasincethefirstquarterof1982isavailableinFigureA.17intheAppendix. To nowcast the business cycle using the wide range of information embedded in this network, we must convert network information into “useful” time series data. We do so in two steps. First, we describe the network using a wide set of network and node metrics. By observing the evolution of these measures over time, we can easily convert them into time-series. In the second step, the vast number of network measures has to be reduced. Our network is described by 5,002 time series, which
ECB Working Paper Series No 2494 / November 2020 18

contain a considerable amount of noise. We apply machine learning techniques as standard econometrics cannot deal with such a sizeable dataset, owing to the “curse”
of dimensionality (see, for example, Giannone et al. (2018)). We first eliminate uninformative signals that have characteristics that do not change over time (constant or semi-constant), thenweallowforfurtherstatisticaldataselectionmakinguseofRFE. Dimension reduction techniques help to isolate relationships that are highly cyclical and that can be applied to predict recessions or periods of high and low growth.

Figure 5 Node-specific network measures vs GDP growth
3 0
-2
-4
-6
-8
Q1-1982 Q1-1983 Q1-1984 Q1-1985 Q1-1986 Q1-1987 Q1-1988 Q1-1989 Q1-1990 Q1-1991 Q1-1992 Q1-1993 Q1-1994 Q1-1995 Q1-1996 Q1-1997 Q1-1998 Q1-1999 Q1-2000 Q1-2001 Q1-2002 Q1-2003 Q1-2004 Q1-2005 Q1-2006 Q1-2007 Q1-2008 Q1-2009 Q1-2010 Q1-2011 Q1-2012 Q1-2013 Q1-2014 Q1-2015 Q1-2016 Q1-2017 Q1-2018 Q1-2019
egnahC
tnecreP
Notes: The graph illustrates various illustrative firm-specific stock network measures derived from daily returns
(dashed blue lines) and the annualised quarterly growth rate of the economy (dashed black-red line). The red bars indicateperiodsofnegativegrowth. After the “translation”, and as illustrated in Figure 5, a set of best-performing measuresisusedtopredictthecycle.

Thebusinesscycledataconsistofseasonallyadjusted quarterly real GDP growth figures (annualised rate) for the United States from the FRED database.10 We consider both aggregate and disaggregate (firm-specific)
characteristics of the network and let the algorithm decide which are most helpful for classification. During expansions we expect shocks to returns to be firm-specific and lesscorrelatedacrossfirms. Sincetheeconomytendstobeashockabsorberinnormal times, our network should appear less aggregated. However, during downturns shocks might propagate across firms, thereby hitting the economy broadly and in a persistent manner.

While aggregate measures can hardly reflect these granular developments,
10 The series identifier in the Federal Reserve Economic Data (FRED) database is A191RL1Q225SBEA. ECB Working Paper Series No 2494 / November 2020 19

we postulate that pooling node-specific patterns in the networks can capture those dynamics well. Furthermore, economic downturns can be detected earlier in specific firms and sectors. Using the aforesaid metrics, we describe in this section the evolution of some aspects of the network. In particular, we discuss measures of the behaviour of the aggregate network and of single nodes or firms.

3.4.1 Aggregate measures
Figure 6 Real GDP growth rate vs dynamic causality index for the S&P 500
0.07
0.06
0.05
0.04
0.03
0.02
0.01
23456789012345678901234567890123456789
88888888999999999900000000001111111111
99999999999999999900000000000000000000
11111111111111111122222222222222222222
1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1-1QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ
ICD
-2
-4
-6
-8
egnahC
tnecreP
3m 6m 12m 18m 24m Real GDP Growth
Notes: TheredbarsindicateperiodsofnegativeGDPgrowth. Thedifferentseriesdisplaydynamiccausalityindexes for different rolling windows bandwidths (i.e. 3, 6, 12, 18 and 24 months) and at a significance level of 1%. The dashedblacklinedisplaystheseasonallyadjustedannualisedquarterlyrealGDPgrowthrate.

Figure 6 displays the dynamic aggregate behavior of the networks at the 1% confidence level for different rolling window bandwidths. The red bars represent periods of negative growth. Focusing on bust periods, it is possible to observe differences in the dynamic causality indexes (DCI) for different bandwidths. The measure computed with 24 months bandwidth seems to react early to big changes, but it is also very persistent which is problematic in an environment of increased volatility of connectedness. On the other hand, the measure with the shortest bandwidth (3 months)
ECB Working Paper Series No 2494 / November 2020 20

misses the downturns. For this reason, we could expect dynamic causality indexes using intermediate bandwidths (i.e. 6 and 12 months) to have higher explanatory power. Besides peaking in periods with below zero growth (recessions) mostly, all measures tend to also peak in boom periods. For example, all dynamic causality indices peak in 1987:Q4 (when the stock market crashed), but this didn’t lead to a slowdown in growth. The same happens for the peaks in 2000 and 2005. For this reason, we argue that the DCI computed at the level of the whole network is too noisy to predict economic activity. 3.4.2 Firm- or node-specific measures
The most granular way to display information from the network is to evaluate the position of the individual nodes.

Displaying connectedness at the node level over time is a rather difficult exercise owing to noise. Moreovoer, to isolate cyclical connectedness, we need to look at network topologies over time. For illustrative purposes
Figure 7 displays the hubs centrality measure for MetLife, a large insurer, as well as the authorities centrality measure for Loews, a conglomerate dealing with insurance, pipeline transport, oil drilling and hotels. Furthermore, we show the PageRank measure for Northrop Grumman, which is an aerospace and defense technology company, and the PageRank measure for Hasbro, the largest toy maker in the world. These companies tend to have a central position in the stock network during recessions or periods of negative growth (e.g. Great Recession).

3.5 Feature normalisation and recursive feature elimination
It is important to have some flexibility when choosing from the wide range of centralitymeasures; whileallmeasuresareintendedtorevealimportantnodecharacteristics, some might be a better fit when trying to forecast business cycles at different horizons. As we have seen, all the centrality measure try to identify the key company or sector occupying pivotal structural positions within the network which might help us understand business cycle dynamics.11 For this reason, it is of key importance to try to reveal the centrality measures that are more informative on the business cycle. To
11 For a critical review on how centrality measures apply to social networks, see Landherr et al. (2010).

ECB Working Paper Series No 2494 / November 2020 21

Figure 7 Firm-specific network measures
2891-1Q 3891-1Q 4891-1Q 5891-1Q 6891-1Q 7891-1Q 8891-1Q 9891-1Q 0991-1Q 1991-1Q 2991-1Q 3991-1Q 4991-1Q 5991-1Q 6991-1Q 7991-1Q 8991-1Q 9991-1Q 0002-1Q 1002-1Q 2002-1Q 3002-1Q 4002-1Q 5002-1Q 6002-1Q 7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
MetLife: Hubs
2891-1Q 3891-1Q 4891-1Q 5891-1Q 6891-1Q 7891-1Q 8891-1Q 9891-1Q 0991-1Q 1991-1Q 2991-1Q 3991-1Q 4991-1Q 5991-1Q 6991-1Q 7991-1Q 8991-1Q 9991-1Q 0002-1Q 1002-1Q 2002-1Q 3002-1Q 4002-1Q 5002-1Q 6002-1Q 7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
Northrop Grumman: Pagerank
2891-1Q 3891-1Q 4891-1Q 5891-1Q 6891-1Q 7891-1Q 8891-1Q 9891-1Q 0991-1Q 1991-1Q 2991-1Q 3991-1Q 4991-1Q 5991-1Q 6991-1Q 7991-1Q 8991-1Q 9991-1Q 0002-1Q 1002-1Q 2002-1Q 3002-1Q 4002-1Q 5002-1Q 6002-1Q 7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
Hasbro: Pagerank
2891-1Q 3891-1Q 4891-1Q 5891-1Q 6891-1Q 7891-1Q 8891-1Q 9891-1Q 0991-1Q 1991-1Q 2991-1Q 3991-1Q 4991-1Q 5991-1Q 6991-1Q 7991-1Q 8991-1Q 9991-1Q 0002-1Q 1002-1Q 2002-1Q 3002-1Q 4002-1Q 5002-1Q 6002-1Q 7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
Loews: Authorities
Notes: Theblacklinesdisplayfirm-specificmeasuresofcentralityasoutlinedinthesubtitles.

Theredbarsindicate periodsofnegativegrowth. Thenetworkmeasuresarederivedfroma12-monthrollingwindowbandwidthanda1%
levelofsignificance. do so, we employ a feature selection method to discard all uninformative measures in the context of our nowcasting exercise.12
We summarise the network measures in the vector of explanatory variables X, the so called feature matrix which comprises 5,002 features in total.13 In a first step, we manually remove all features exhibiting too low variance. After eliminating uninformative features, the X vector in our model contains about 4,104 features, each providing 149 time observations from the first quarter of 1982 until the first quarter of
2019. We standardise the features to have a zero mean and a standard deviation of 1.

Then we let algorithms, so called dimension reduction techniques, decide which features can improve predictive performance. In particular, we apply RFE as shown by Guyon et al. (2002) with a k-fold cross-validation as in Yan and Zhang (2015). 12 Please note that we do not only discard less robust metrics, but also discard useful information that would be helpful at different forecasting horizons. 13 Notethatricherspecificationsmightimprovemodelperformance. AmongothersDavigandHall(2019)
includingarichlagstructureinmachinelearningset-ups. Thiscouldbeapromisingavenueforfuturework as predictive information might be available several quarters before, which are in the current nowcasting setup only inadequately reflected.

In alternative specifications, we have used a multitude of rolling window sizes and significance levels of the same network. While this can clearly enhance model performance it is computationally very costly. Therefore, we decided to discuss our findings based on reduced data-sets with5,002features. Thisnumberstemsfrom500companiestimestennode-specificmeasures(betweenness, degree, in-degree, out-degree, hubs, authorities, pagerank, closeness, in-closeness, out-closeness) and two aggregate measures (dynamic causality index, cluster coefficient). ECB Working Paper Series No 2494 / November 2020 22

RFEisaclassicalalgorithminmachinelearningusedtoselectthemostrelevantsetof features (variables) in a model. Unlike dimension reduction methods (e.g. principal components analysis), feature selection methods do not transform the features into a lower dimension, but rather remove those features discovered by the model to be of least importance. This step is very important because we are not imposing any structure on our model (e.g. conditioning the behaviour of the dependent variable into a set of variables that we have previously selected) but rather we are letting the model choose for us the hidden or unknown behavior that produces higher accuracy
(that predicts GDP growth rates in our case).

To achieve this, we first need to remove all variables that are irrelevant, insignificant or unimportant to the model. In particular. the algorithm removes weak features in each iteration until it has found the optimal combination according to the F1 score.14 This method performs well for our task as our features are (noisy) proxies of economy-wide shocks which require to be evaluated in pools. The algorithm is designed to use at least five features.

RFE
is an established and rigorous method for identifying relevant features before feeding them into a machine learning algorithm which reduces the problem of overfitting (or underfitting).15 To overcome the criticism of introducing information which was not known in that period, in order to select signals that are deemed optimal today, apply k-fold cross-validation to show that in each combination of sub-periods the measures must be optimal. 3.5.1 Model specification
The vector Y is given by (i) a binary model where negative annualised quarterly
GDP growth rates take the value 1, while all other periods take the value 0:

 1 negative growth if QGDP < 0
Y = (5)
 0 normal if QGDP ≥ 0
14 TheF1scoreisdefinedastheharmonicmeanofprecisionandrecall.

Precisionisdefinedasthenumber of true positives over the number of true positives plus the number of false positives. Recall is defined as the number of true positives over the number of true positives plus the number of false negatives. 15 WhileourY cantakethebinaryform(negativegrowthanditscomplement)ortheternaryform(high, low and negative growth periods). All cases will be defined in the next subsection. ECB Working Paper Series No 2494 / November 2020 23

or (ii) high, low and negative growth (HLN) as specified in Equation 6 for low growth where the rate is less than 0%, normal (between 0% and 3%), and high (more than
3%)16:

 2 high if QGDP > 3.0
  k

Y = 1 negative if QGDP < 0 (6)


  0 low if QGDP ≤ 3.0 and QGDP ≥ 0
We use data from the first quarter of 1982 to the fourth quarter of 2006 as training data and nowcast, using contemporaneous information from the current quarter, on an expanding window all periods from the first quarter 2007 to the first quarter of
2019. 3.5.2 The classifiers
In this subsection, we briefly describe the classifiers used in this study.

The naive Bayes (NB) classifier is a widespread method in machine learning applications.17 According to Bayes’ theorem:
P(Y )P(X|Y )
P(Y |X) = (7)
P(X)
with Y representing the k-th class, in our case periods with below zero growth or recession periods, while X=x ,....,x are n observed variables, which are our fea1 n tures. Assuming that the explanatory variables are independent, P(Y )P(X|Y ) can be expressed as:
(cid:89)
P(Y )P(x |Y )...P(x |Y ) = P(Y ) P(x |Y ) (8)
k 1 k n k k i k
The approach is called naive because the observations are assumed to be independent,
16ItistobenotedthatweabstractfromNBERrecessionsinthisstudyasweareusingnon-standarddata at a higher frequency for which this definition would appear somewhat artificial with conventional setups.

WeperformedtheRFEexerciseswithNBERdataalsoandweidentifiedastrongerimpactonmanufacturing as compared with the negative growth periods case. 17 See Jordan and Mitchell (2015), Hagenau et al. (2013) and Heiberger (2018). ECB Working Paper Series No 2494 / November 2020 24

while in reality they are not. However, the violation of this assumption would have only minimal consequences for the predictive ability of this Bayesian approach, and on the contrary could even contribute to improving it as shown by Rish et al. (2001). ˆ
From Equation 1 and 7, we can derive the decision rule on how to assign a class Y
to a set of observations X with
(cid:89)
ˆ
Y = argmax P(Y ) P(x |Y ) (9)
k∈(1,..,k) k i k
Davig and Hall (2019) showed that this simple technique can outperform logistic regressions in recession forecasting. This is due to the fact that it converges faster to its asymptotic error rate than, for example, logistic regression. This is an important advantage in applications with a short data span.

Support vector machines
Support vector machine (SVM) analysis is a popular machine learning tool for classification and regression, developed in 1992 by Boser et al. (1992). SVMs belong to the family of generalised linear classifiers. They are a prediction tool that uses machine learning theory to maximise predictive accuracy while automatically avoiding over-fitting to the data. SVM can be defined as systems which use a hypothesis space of linear functions in a high dimensional feature space, trained with a learning algorithm from optimisation theory that implements a learning bias derived from statistical learning theory. In other words, classes are separated by hyperplanes where the distance to the nearest elements of each class is the largest.

ThemainadvantageofusingSVMisthatasnon-parametrictechnique, itdoesnot require to assume certain conditions or parameters in the data (e.g. linear combinations or lack of heteroscedasticity in our sample). SVM uses the principle of maximal margin, meaning that we are not so concerned about the prediction as long as the error term ((cid:15)) is less than a certain value. Put differently, maximal margin allows
SVM to be viewed as a convex optimisation problem. Moreover, the regression can also be penalised using a cost parameter (as explained in more detail later), which helps to avoid over-fitting. Nevertheless, a shortcoming of the SVM model is that it
ECB Working Paper Series No 2494 / November 2020 25

places observations above and below a classifying hyperplane and there is therefore no direct probabilistic interpretation.18 It should be noted that we do not rely on approximated probabilities, for this reason we calculate our test statistics and plot the predicted outcome. To keep things simple, we use a linear kernel function to map lower dimensional data into a higher dimensional space: u(cid:48)v, where u(cid:48) and v are the vectors representing the inputs in the vector space. In addition, we set the cost of constraints violation to
0.5. This is the ’C’-constant of the regularisation term in the Lagrange formulation, or in other words, the extent to which misclassifying is to be avoided in each training example.

For large values of C, the optimisation will choose a smaller-margin hyperplane of that hyperplane which does a better job. Logistic regression
Logistic regression (LR) (see Equation 10) is commonly used to model the probability of a certain event and is a natural benchmark. Contrary to a linear regression, a logistic regression is bounded between 0 and 1. It thus provides a probability score that reflects the probability of the occurrence of an event. ez eα+βiX
P(Y |X) = E(Y |X) = = (10)
k k 1+ez 1+eα+βiX
The nowcasting of GDP turning points with our approach faces two major difficulties. First, a major challenge is to identify the correct signals in a very noisy environment. This step is managed by RFE.

Given the shortness of the time-series of macroeconomic data, this approach is often criticised for using information which is not known in the past, e.g. cyclical node positions. However, by applying k-fold cross-validation, the criticism of selecting the best model using information available today but not known at the time is reduced, since the correct variables must also be valid when applied to prior subsets of data. Moreover, in an additional exercise we apply RFE in an out-of-sample consistent fashion.Second, given the availability of highly qualitative signals, it is still difficult to detect events in real-time that propagate slightly differently. 18Nevertheless, approximations of probabilities of outcomes exist, e.g. Platt (1999).

ECB Working Paper Series No 2494 / November 2020 26

4 Nowcasting US business cycles
The following subsections present the results (in-sample and out-of-sample) for the binary and the ternary state model for nowcasting turning points in GDP. 4.1 In-sample feature selection and prediction
This subsection selects optimal features taking into account the whole sample including the out-of-sample period and splitting it into k-folds. 4.1.1 Two-state model: detecting negative growth
In this subsection, we nowcast periods of negative growth as specified in Equation
5. We apply a battery of models such as SVM, NB and LR on RFE-selected data.

Figure 8 displays the outcome of an out-of-sample nowcasting exercise starting from
Figure 8 Real-time forecast, negative growth, three methods
7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
Support Vector Machines
Logistic Regression
Note: The graph displays probabilities of negative growth periods as calculated in an expanding window. For predictingt(fromthefirstquarterof2007tothefirstquarterof2019)wetakeintoaccountnetworkinformationuntil t, whiletrainingdatarangesfromthefirstquarterof1982toperiodt-4. Theredbarsindicatehistoricalperiodsof negativegrowth. FeaturesareselectedwithRFEuntilthefirstquarterof2019withfivefolds.

the first quarter of 2007 based on RFE feature selection over the entire sample until the first quarter of 2019.19 We make use of RFE to select the most informative set
19 The features are selected by using a method that is well-known in machine learning: recursive feature elimination, with k-fold cross-validation with k=5. The RFE algorithm divides the data into groups and evaluates the performance of the model on subgroups of data, while predicting 1 out of k folds. The k-fold cross-validation ensures that features would have also been regarded as optimal in different sub-periods prior the first quarter of 2007.

In addition, it also provides the optimal number of features with specific properties dealing with the trade-off of adding information, while reducing noise, information redundancy,
ECB Working Paper Series No 2494 / November 2020 27

of features for a given matrix of features X and a response variable Y. The SVM
algorithm captures the turning points and other periods very well, while the naive
Bayes produces few false positives and the logistic regression does not capture the initial period of the contraction during the financial crisis. Parts of the remaining inaccuracies stem from the fact that the data-set is large, containing 4,100 features, and from the standardisation of features, which make it hard for naive Bayes and logistic regression to process the information correctly.

Figure 9 Properties most informative features, negative growth
Authorities Betweenness Degree Centrality Hubs In-degree Out-closeness Out-degree Pagerank
Manufacturing Transportation Retail Finance Services
Notes: Thegraphdisplaysthepropertiesofthe16featureswiththehighestexplanatorypowerforpredictingperiods withnegativegrowth. Eachsubplotistobeinterpretedindependently. Theysummariseinformationonthetypeof measureandtowhichsectorsthefeaturesrelateto. The conditional probabilities P(Y |X ) are ranked by their explanatory power. kt it
In the case of negative growth periods, the algorithm favours 16 features (see Figure
A.19 in the Appendix). In an ex-post evaluation, we summarise the properties of the selected features for the real-time forecast (nowcast) model.

Figure 9 at the top shows the properties of the selected measures. The features used for prediction are mostly selected from among the hubs, in-degree and PageRank metrics. All these measures emphasise the high importance of centrality and they assign a high weight to pivotal companies in the economy, whose returns are linked directly or indirectly to many and overfitting. Using RFE in each period would add noise and make it harder to capture turning points, while at the same time it is also less computationally efficient. ECB Working Paper Series No 2494 / November 2020 28

and influential companies and which hence provide early signals for economy-wide developments. The algorithm selects features from the finance and manufacturing sectors. Table A.3 in the Appendix displays the individual properties of the features such as the measure, significance and bandwidth levels, the company and the sector it belongs to. For example, one of the selected features is associated with MetLife, one of the largest global providers of insurance, annuities and employee benefit programmes. This is very intuitive as insurers like MetLife are exposed to economy-wide developments owing to their shareholdings in a wide variety of companies.

Similarly, with regard to services, Akamai Technologies is one of the largest content delivery network (CDN), cyber-security and cloud service providers, which are exposed to cyclical demand. On the manufacturing side, we select Dentsply Sirona, one of the world’s largest dental equipment makers and dental consumables producers, and Amgen, a multinational bio-pharmaceutical company. Both are part of the health-care sector, which is very sensitive to developments in economic activity.

The selection of hubs, PageRank and authorities measures as being more informative for predicting negative growth periods suggests that developments in returns of these companies influence the returns of many other companies that are not necessarily connected to each other.20
4.1.2 Three-state model: high, low and negative growth
In this subsection, we extend the model to a ternary outcome as specified by Equation 6. The RFE algorithm proposes six features to be optimal. Figure 10 reveals the properties of the selected features. There is a strong emphasis on companies related to finance, which includes banks and insurers. With respect to the measures, the algorithm again favours hubs, PageRank and authorities measures.

20Additionalanalysisrevealsthatwithvaryingsignificancelevelscyclicalitymightbebetterapproximated by different measures of centrality, while the node-position of an company remains unaltered. For example
MetLife out-degree is regarded as cyclical by this algorithm at a significance level of 1% with the feature beingstandardised,whileat5%withthefeaturebeingnormalisedthealgorithmdetectscyclicalinformation in the hubs measure associated with this company. The latter case is illustrated in Figure 7. ECB Working Paper Series No 2494 / November 2020 29

Figure 10 Properties most informative features, high, low and negative growth
1.5
0.5
Authorities Hubs Out-closeness Pagerank
Retail Finance
Notes: Thegraphdisplaysthepropertiesofthesixselectedfeatureswiththehighestexplanatorypowerforpredicting periodswithHLNgrowth. Eachsubplotistobeinterpretedindependently. Theysummariseinformationonthetype ofmeasureandtowhichsectorsthefeaturesrelateto. Figure 11 displays the predicted probabilities for two of the three states. All three algorithms perform well despite the fact that there are a few false positives in the high growth probability case. Furthermore, logistic regressions have a harder time to interpret the data, providing elevated estimates in the post-crisis period.

Surprisingly, the naive Bayes model captures the turning points well and produces few false positives. Table A.5 in the Appendix displays the details of the selected features. As in the negative growth model, the MetLife hubs measure is selected. The Unum Group is another insurer, SVB Financial is a commercial bank that has specialised in lending to high-tech companies and UnitedHealth Group offers health care products and insurance services. UDR is a publicly traded real estate investment trust that invests in apartments, while Home Depot is the largest home improvement retailer in the
United States. ECB Working Paper Series No 2494 / November 2020 30

Figure 11 High, low and negative growth probability, real-time forecast, three methods
7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
hgiH
Notes: Thegraphdisplaysprobabilitiesofhighandnegativegrowthperiodsascalculatedinanexpandingwindow. Forpredictingt(fromthefirstquarterof2007tothefirstquarterof2019)wetakeintoaccountnetworkinformation untilt,whilethetrainingdatarangeisfromthefirstquarterof1982toperiodt-4. Theredbarsindicatehistorical periods of negative growth and the green bars indicate high growth (above 3%). For the SVM model, we plot the predictedoutcome. FeaturesareselectedwithRFEuntilthefirstquarterof2019withthreefolds.

4.2 Out-of-sample consistent feature selection and prediction
Althoughk-foldcross-validationrequiresfeaturestobeoptimalinsubsetsoftheentire time span - including sub-periods that occur only before the start of the nowcasting exercise - we acknowledge the criticism of potentially working with information that would not have been known at this time. Therefore, in this exercise we only employ features that would have been regarded as optimal based solely on information that was available up the fourth quarter of 2006 and we conduct the out-of-sample nowcasting exercise starting in the first quarter of 2007.

4.2.1 Two-state model: detecting negative growth
Figure 12 displays the outcome of a nowcasting exercise starting from the first quarter of2007withfeaturesbeingselectedbeforethefourthquarterof2006. Apparently,this version of the binary model would not immediately capture the onset of the Great Recession, but would otherwise perform relatively well. Therefore, we can assume that the selected features have been stable in their provision of signals regarding economic growth. As expected, the overall performance of the measures is worse relative to the performance of the complete sample RFE based binary model. Figure 13 summarises the properties of the 32 features selected as illustrated in Table A.4 in the Appendix. ECB Working Paper Series No 2494 / November 2020 31

Features from the manufacturing industry (including pharmaceutical companies and durable goods manufacturing companies) and features from the transportation, retail and financial sectors are chosen. The features selected from the manufacturing sector are mostly measures of degree centrality, while the features selected from retail, transportation and financial firms are chosen from the PageRank measure. Figure 12 Real-time forecast, negative growth, three methods
7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
Support Vector Machines
Logistic Regression
Note: The graph displays probabilities of negative growth periods as calculated in an expanding window.

For predictingt(fromthefirstquarterof2007tothefirstquarterof2019)wetakeintoaccountnetworkinformationuntil t,whilethetrainingdatarangeisfromthefirstquarterof1982toperiodt-2. FeaturesareselectedwithRFEuntil the fourth quarter of 2006. The red bars indicate historical periods of negative growth. Features are selected with
RFEuntilthefourthquarterof2006withthreefolds. 4.2.2 Three-state model: high, low and negative growth
Figure 14 displays the predicted probabilities for two of the three states at the out-ofsample horizon, employing features that are optimal until the fourth quarter of 2006. We observe a significant loss in efficiency, although the turning point of the financial crisis is still nowcasted.

We find many false positives for the negative growth state, however, they correspond to very low (although non-negative) growth. The same holds true for cases of positive growth. Figure 15 summarises the properties of the 12 features selected as illustrated in
Table A.6 in the Appendix. Most features relate to the manufacturing, retail and services sectors, while the network measures are broad-based with the PageRank
ECB Working Paper Series No 2494 / November 2020 32

Figure 13 Properties most informative features, negative growth
Authorities Betweenness Degree Centrality Hubs In-degree Out-degree Pagerank
Primary & Constr. Manufacturing Transportation Wholesale Retail Finance Services
Notes: Thegraphdisplaysthepropertiesofthe32featureswiththehighestexplanatorypowerforpredictingperiods of negative growth. Each subplot is to be interpreted independently. They summarise information on the type of measureandtowhichsectorsthefeaturesrelateto.

Figure 14 High, low and negative growth probability, real-time forecast, three methods
Support Vector Machines
Logistic Regression
7002-1Q 8002-1Q 9002-1Q 0102-1Q 1102-1Q 2102-1Q 3102-1Q 4102-1Q 5102-1Q 6102-1Q 7102-1Q 8102-1Q 9102-1Q
hgiH
Notes: Thegraphdisplaysprobabilitiesofhighandnegativegrowthperiodsascalculatedinanexpandingwindow. Forpredictingt(fromthefirstquarterof2007tothefirstquarterof2019)wetakeintoaccountnetworkinformation until t, while the training data ranges from the first quarter of 1982 to period t-2. The red bars indicate historical periods of negative growth and the green bars indicate high growth (above 3%). For the SVM model, we plot the predictedoutcome. FeaturesareselectedwithRFEuntilthefourthquarterof2006withthreefolds. measure again being predominant.

The home improvement retailer Home Depot is once again among the selected features. ECB Working Paper Series No 2494 / November 2020 33

Figure 15 Properties most informative features, high, low and negative growth
Authorities Betweenness Degree Centrality In-closeness Out-closeness Out-degree Pagerank
Manufacturing Transportation Retail Services
Notes: Thegraphdisplaysthepropertiesofthe12featureswiththehighestexplanatorypowerforpredictingperiods with HLN growth. Each subplot is to be interpreted independently. They summarise information on the type of measureandtowhichsectorsthefeaturesrelateto. 4.3 Algorithm performance comparison
In this subsection, we evaluate the performance of the different algorithms in an outof-sample nowcast exercise. As correct probabilities for the SVM classification do not exist, we use the predicted outcome which restricts somewhat comparability with the other algorithms.

We apply four different metrics: i) the average precision score that summarises a precision-recall curve as the weighted mean of precision achieved at each threshold
(this is done by using the increase in recall from the previous threshold as a weight); ii) the area under the receiver operator curve (AUROC): the higher the area, the better the model is at separating classes; iii) the mean squared error (MSE), which is a risk metric that corresponds to the value of the squared (quadratic) error or loss
(it is always non-negative, and values closer to zero are better); and iv) the accuracy score, which is the fraction of correct predictions.

Table 2 illustrates the performance of the different algorithms for the two models where (i) RFE was conducted on the entire sample and (ii) where RFE was run on the data up to the fourth quarter 2006. Overall, case (ii) - the true out-of-sample
ECB Working Paper Series No 2494 / November 2020 34

Table 2 Real-time forecast, model evaluation. Metric/Algorithm Negativegrowth HLNgrowth in-sampleRFE out-of-sampleRFE in-sampleRFE out-of-sampleRFE
AveragePrecisionScore
SVM 1.00∗ 0.41∗ 0.57∗ 0.44∗
NB 0.90 0.33 0.56 0.50
LR 0.98 0.42 0.76 0.55
AUROC
SVM 1.00∗ 0.76∗ 0.77∗ 0.66∗
NB 0.97 0.62 0.65 0.69
LR 0.99 0.76 0.83 0.68
MeanSquaredError
SVM 0.00 0.26 0.72 0.98
NB 0.09 0.21 1.04 1.43
LR 0.02 0.19 0.91 0.85
AccuracyScore
SVM 1.00 0.74 0.66 0.53
NB 0.91 0.78 0.60 0.47
LR 0.98 0.81 0.47 0.53
Notes: TheaverageprecisionscoreandtheAUROCarederivedbasedonpredictedprobabilities. Wedecidetokeep thepredictedoutcomefortheSVMmodelandnottoprovideapproximateprobabilities. Themeasuresaffectedare indicated with an asterisk ∗.

The mean squared error and the accuracy score are based on the predicted outcomes, whichpreservesfullcomparabilitybetweenthemeasuresforallalgorithms. exercise - displays a weaker performance. For case (i), in the negative growth case,
SVMoutperformsthenaiveBayesandthelogisticregression. Asexpectedthelogistic regression behaves very similarly to SVM, but might have some problems with the standardisation. Visual inspection reveals that both algorithms are very efficient, but
SVMcapturestheturningpoints. Intheternarystatemodel, theSVMalgorithmand the logistic regression capture the negative growth periods, in particular the turning points very well. However, they also produce false positives which mostly relate to periods of a weaker growth momentum.

In particular, the logistic regression displays a high persistency in probabilities of false positives in the negative growth probability case. On the other hand, the naive Bayes does not produce as many false positives, but also misses some true positives. For case (ii), in the negative growth model the logisticregressionperformsbetterinallmeasures, whileSVMisslightlyworserelative to the AUROC and the average precision score. In the three-states model, the logistic regression and the naive Bayes model have a much higher average precision score and a slightly higher AUROC than SVM. Overall, the results show that SVMs perform best in in-sample analysis, since this method is prone to overfitting. But in true out-of-sample forecasting, logistic regression and naive Bayes outperform SVM.

ECB Working Paper Series No 2494 / November 2020 35

5 Concluding remarks
Employing machine learning methods, we exploit the forward-looking behaviour of financial market information to identify the current state of the economy. We construct a dynamic network based on pairwise Granger causalities of stock returns of the constituents of the Standard & Poors 500 index. By calculating the topology of the network we create a “fat” data-set of 5,002 time-series, which we evaluate with machine learning methods. Once cyclical patterns in the network are identified, different classifiers (naive Bayes, support vector machines and logistic regression) are used to predict different economic regimes in real time (e.g. expansions and recessions).

The advantages of the proposed method are the following: (i) the network structure is able to capture the non-linear nature of shock propagation in the economy; (ii)
the network contains many relationships in the economy, including some that might not have received attention before; (iii) pooling node-level information provides a mechanism that is more robust to the “every cycle is different” criticism; and (iv) the advantage of using financial data is that they are forward looking, non-proprietary and provided in real-time. Most importantly, they are not subject to larger revisions and reflect market expectations about economic fundamentals as well as the shortterm outlook, which makes them ideal for nowcasting and forecasting.

Weinnovateuponexistingapproachesby: (i)employingpairwiseGranger-causality networks as opposed to mere correlations, thereby taking into account directionality and statistical significance; (ii) allowing for many measures of centrality at the aggregate and node-level, but finally selecting fewer features than in comparable studies, potentially reducing the problem of overfitting; (iii) comparing different algorithms; and (iv) performing an exercise in which we compare the in-sample and out-of-sample stability of features. We analyse two models. The first tries to identify two economic regimes: “recession” (defined as negative growth in the quarter) and its complement.

In the second model, we try to perform the more challenging task of distinguishing between three
ECB Working Paper Series No 2494 / November 2020 36

regimes: “low growth” (defined as negative growth in the quarter), “low growth”
(defined as non-negative, but lower than high growth) and “high growth” (defined as annualised growth of 3% in the quarter). Our findings suggest that our network approach can help to detect changes in economic regimes in real-time giving policymakers a tool to anticipate slowdowns and take measures against them. The main findings can be summarised as follows: (i) Applying RFE on the entire sample, we are able to determine ex-post which firms were exposed to earnings shocks that turned into aggregate fluctuations. Looking at the sectors where these firms operate, a more complete narrative can be derived than is the usually derived from more aggregate data.

The two-state model for predicting periods of negative growth can predict future states remarkably well by using information from the node-positions of manufacturing firms, transportation firms and financial firms, particularly insurance firms. The ternary state model successfully predicts economic regimes by making use of information from the financial sector, the insurance subsector, and the retail sector. (ii) Using features that are selected to be optimal until the fourth quarter of 2006
(i.e. excluding the out-of-sample period), we validate our models in terms of true out-of-sample nowcasting performance and verify that the in-sample results are not solely due to favorable feature selection.

While the predictions of the binary state model are weaker, the ternary state model captures the turning point of the great recession and performs well overall, despite producing some false positives for the negative growth state in periods of weak growth. There are many ways to improve upon and extend the current framework. Stock marketreturnsnetworksprovidetimelysignalsandimplicitlyincludeforward-looking information. However, they provide a somewhat narrow view of economic developments. Including features that could better capture the financial cycle21 or a different measurement of spillovers, such as transfer entropy or directed volatility spillovers, as proposed by Diebold and Yılmaz (2014), might deliver stronger signals.

Furthermore, robustness exercises have shown that different rolling window bandwidths of 3 to 18
months could be promising variants to use. As computational efficiency and feature
21 Lang et al. (1996) find a negative relationship between high leverage and future firm growth. Berger and Udell (1998) show that for small firms different capital structures are optimal at different points in the cycle. ECB Working Paper Series No 2494 / November 2020 37

engineering is vital in this setup, a clear taxonomy of dimension reduction techniques could further improve the models’ performance.
ECB Working Paper Series No 2494 / November 2020 38

References
Acemoglu,D.,V.M.Carvalho,A.Ozdaglar,andA.Tahbaz-Salehi.2012. Thenetwork origins of aggregate fluctuations. Econometrica Vol. 80, Issue 5: 1977–2016. Adam, K., and S. Merkel. 2019. Stock price cycles and business cycles. ECB Working
Paper Series No 2316, ECB, Frankfurt am Main, September. Adrian, T., N. Boyarchenko, and D. Giannone. 2019. Vulnerable growth. American
Economic Review Vol. 109, Issue 4: 1263–1289. Alessi, L., and C. Detken. 2011. Quasi real time early warning indicators for costly asset price boom/bust cycles: A role for global liquidity. European Journal of
Political Economy Vol. 27, Issue 3: 520–533. Berger, A. N., and G. F. Udell. 1998. The economics of small business finance: The roles of private equity and debt markets in the financial growth cycle.

Journal of
Banking & Finance Vol. 22, Issue 6-8: 613–673. Bernanke, B. S., M. Gertler, and S. Gilchrist. 1999. The financial accelerator in a quantitative business cycle framework. Handbook of Macroeconomics Vol. 1, Part
C: 1341–1393. Billio, M., M. Getmansky, A. W. Lo, and L. Pelizzon. 2012. Econometric measures of connectedness and systemic risk in the finance and insurance sectors. Journal of
Financial Economics Vol. 104, Issue 3:35–559. Boser, B. E., I. M. Guyon, and V. N. Vapnik. 1992. A training algorithm for optimal margin classifiers pp. 144–152. Camacho, M., G. Perez-Quiros, and P. Poncela. 2018. Markov-switching dynamic factor models in real time. International Journal of Forecasting Vol. 34, Issue 4:
598–611. Chauvet, M., and J. Hamilton. 2006.

Dating business cycle turning points. in Milas,
C. P. Rothman and D. van Dijk (eds), Nonlinear Time Series Analysis of Business
Cycles 276. ECB Working Paper Series No 2494 / November 2020 39

Davig, T., and A. S. Hall. 2019. Recession forecasting using Bayesian classification. International Journal of Forecasting Vol. 35, Issue 3: 848–867. Diebold, F. X., and K. Yılmaz. 2014. On the network topology of variance decompositions: Measuring the connectedness of financial firms. Journal of Econometrics
Vol. 182, Issue 1: 119–134. Drehmann, M., andM.Juselius.2014. Evaluatingearlywarningindicatorsofbanking crises: Satisfying policy requirements. International Journal of Forecasting Vol. 30,
Issue 3: 759–780. Duca, M. L., and T. A. Peltonen. 2013. Assessing systemic risks and predicting systemic events. Journal of Banking & Finance Vol. 37, Issue 7: 2183–2195. Ferreira, T. 2018. Stock market cross-sectional skewness and business cycle fluctuations.

FRB International Finance Discussion Papers No. 1223. Gabaix, X. 2011. The granular origins of aggregate fluctuations. Econometrica Vol. 79, Issue 3: 733–772. Giannone, D., M. Lenza, and G. E. Primiceri. 2018. Economic predictions with big data: The illusion of sparsity. Tech. Rep. 847. Giusto, A., and J. Piger. 2017. Identifying business cycle turning points in real time with vector quantization. International Journal of Forecasting Vol. 33, Issue 1:
174–184. Gourinchas, P.-O., and M. Obstfeld. 2012. Stories of the twentieth century for the twenty-first. American Economic Journal: Macroeconomics Vol. 4, Issue 1: 226–65. Granger, C. W. 1969. Investigating causal relations by econometric models and crossspectral methods. Econometrica Vol. 37, Issue 3: 424–438. Granger, C. W. 1979.

Forecasting in business and economics. Elsevier Monographs . Guyon, I., J. Weston, S. Barnhill, and V. Vapnik. 2002. Gene selection for cancer classification using support vector machines. Machine Learning Vol. 46: 389–422. ECB Working Paper Series No 2494 / November 2020 40

Hagenau, M., M. Liebmann, and D. Neumann. 2013. Automated news reading: Stock price prediction based on financial news using context-capturing features. Decision
Support Systems Vol. 55, Issue 3: 685–697. Heiberger, R. H. 2018. Predicting economic growth with stock networks. Physica A:
Statistical Mechanics and its Applications Vol. 489: 102–111. Jordan, M. I., and T. M. Mitchell. 2015. Machine learning: trends, perspectives, and prospects. Science Vol. 349, Issue 6245: 255–260. Landherr, A., B. Friedl, and J. Heidemann. 2010. A critical review of centrality measures in social networks. Business & Information Systems Engineering Vol. 2,
Issue 6: 371–385. Lang, L., E.Ofek, andR.Stulz.1996. Leverage, investment, andfirmgrowth. Journal of Financial Economics Vol. 40, Issue 1: 3–29. Li, J.

2017. Credit market frictions and the linkage between micro and macro uncertainty. Næs, R., J. A. Skjeltorp, and B. A. Ødegaard. 2011. Stock market liquidity and the business cycle. The Journal of Finance Vol. 66, Issue 1:139–176. Ng, S. 2014. Viewpoint: Boosting recessions. Canadian Journal of Economics Vol. 47, Issue 1: 1–34. Plagborg-Møller, M., L. Reichlin, G. Ricco, and T. Hasenzagl. 2020. When is Growth at Risk? Brookings Papers on Economic Activity Spring. Platt, J. 1999. Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. in Smola, A., P. Bartlett, B. Schlkopf and D. Schuurmans (eds.) Advances in Large Margin Classifiers, Cambridge. Qi, M. 2001. Predicting US recessions with leading indicators via neural network model.

International Journal of Forecasting Vol. 17, Issue 3: 383–401. Rish, I., et al. 2001. An empirical study of the naive Bayes classifier. IJCAI 2001
Workshop on Empirical Methods in Artificial Intelligence Vol. 3, Issue 22: 41–46. ECB Working Paper Series No 2494 / November 2020 41

Rose, A. K., and M. M. Spiegel. 2012. Cross-country causes and consequences of the
2008 crisis: Early warning. Japan and the World Economy Vol. 24, Issue 1: 1–16.
Yan, K., and D. Zhang. 2015. Feature selection and analysis on correlated gas sensor data with recursive feature elimination. Sensors and Actuators B: Chemical Vol.
212: 353–363.
Zingales, L. 2015. Presidential address: Does finance benefit society? The Journal of Finance Vol. 70, Issue 4: 1327–1363.
Zou,C.,andJ.Feng.2009. Grangercausalityvs.dynamicBayesiannetworkinference: a comparative study. BMC Bioinformatics Vol. 10, Issue 1: 122.
ECB Working Paper Series No 2494 / November 2020 42

A Additional results
A.1 Data
Figure A.16 Data coverage
0.9
0.8
0.7
0.6
0.5
0.4
0.3
0.2
0.1
1980 1985 1990 1995 2000 2005 2010 2015
seinapmoC
rN#
/ NaN
United States
Notes: The graph displays the amount of NaN series per total amount of companies. Figure A.17 Normalised stable node-relations during phases of the business cycle
104 NBER Recession 105 Non-Recession
4 2
3.5 1.8
1.6
1.4
2.5 1.2
2 1
1.5 0.8
0.6
0.4
0.5 0.2
0 0
0 0.2 0.4 0.6 0.8 0 0.2 0.4 0.6 0.8
Notes: The graph illustrates normalised quarterly connectedness from 1982:Q1 to 2019:Q1 on a 12 month rolling window bandwidth and a 5% significance level. Connectedness in specific nodes in NBER recession periodsaremorepersistentthaninnon-recessionperiods,whereconnectednessmightbemoreidiosyncratic.

ECB Working Paper Series No 2494 / November 2020 43

A.2 Negative growth periods
A.2.1 In-sample RFE
Figure A.18 Optimal number of features (RFE)
0.88 F1 cross-validation score
0.86
0.84
0.82
0.80
0.78
0 1000 2000 3000 4000
Table A.3 Selected features United States, negative growth
ABBOTTLABORATORIES Manufacturing Betweenness 1% 12m
EXELON Transportation DegreeCentrality 1% 12m
METLIFE Finance,InsuranceandRealEstate Out-degree 1% 12m
BECTONDICKINSON Manufacturing In-degree 1% 12m
AKAMAITECHS.

Services In-degree 1% 12m
DENTSPLYSIRONA Manufacturing In-degree 1% 12m
METLIFE Finance,InsuranceandRealEstate Hubs 1% 12m
HUMANA Finance,InsuranceandRealEstate Hubs 1% 12m
STATESTREET Finance,InsuranceandRealEstate Hubs 1% 12m
DOLLARTREE Retail Hubs 1% 12m
KIMCOREALTY Finance,InsuranceandRealEstate Hubs 1% 12m
EXELON Transportation Pagerank 1% 12m
WELLTOWER Finance,InsuranceandRealEstate Pagerank 1% 12m
AKAMAITECHS. Services Pagerank 1% 12m
UDR Finance,InsuranceandRealEstate Out-closeness 1% 12m
LOEWS Finance,InsuranceandRealEstate Authorities 1% 12m
ECB Working Paper Series No 2494 / November 2020 44

A.2.2 Out-of-sample consistent RFE
Figure A.19 Optimal number of features (RFE)
0.95 32
F1 cross-validation score
0.94
0.93
0.92
0.91
0.90
0.89
0 500 1000 1500 2000 2500 3000 3500 4000
Table A.4 Selected features, negative growth
PFIZER Manufacturing Betweenness 1% 12m
ABBOTTLABORATORIES Manufacturing Betweenness 1% 12m
HP Manufacturing DegreeCentrality 1% 12m
DOLLARTREE Retail DegreeCentrality 1% 12m
PEPSICO Manufacturing Out-degree 1% 12m
NIKEB Manufacturing Out-degree 1% 12m
STATESTREET Finance,InsuranceandRealEstate Out-degree 1% 12m
DOLLARTREE Retail Out-degree 1% 12m
NEWMONTGOLDCORP Primary&Construction Out-degree 1% 12m
PROCTER&GAMBLE Manufacturing In-degree 1% 12m
CVSHEALTH Retail In-degree 1% 12m
CERNER Services In-degree 1% 12m
DENTSPLYSIRONA Manufacturing In-degree 1% 12m
NISOURCE Transportation In-degree 1% 12m
STATESTREET Finance,InsuranceandRealEstate Hubs 1% 12m
DOLLARTREE Retail Hubs 1% 12m
CVSHEALTH Retail Pagerank 1% 12m
TJX Retail Pagerank 1% 12m
DUKEENERGY Transportation Pagerank 1% 12m
NORTHROPGRUMMAN Manufacturing Pagerank 1% 12m
COGNIZANTTECH.SLTN.A Services Pagerank 1% 12m
EXELON Transportation Pagerank 1% 12m
SYSCO Wholesale Pagerank 1% 12m
ONEOK Transportation Pagerank 1% 12m
EQUITYRESD.TST.PROPS.SHBI Finance,InsuranceandRealEstate Pagerank 1% 12m
WELLTOWER Finance,InsuranceandRealEstate Pagerank 1% 12m
EVERSOURCEENERGY Transportation Pagerank 1% 12m
HASBRO Manufacturing Pagerank 1% 12m
EXPEDITORINTL.OFWASH.

Transportation Pagerank 1% 12m
TORCHMARK Finance,InsuranceandRealEstate Pagerank 1% 12m
H&RBLOCK Services Pagerank 1% 12m
MCCORMICK&COMPANYNV. Manufacturing Authorities 1% 12m
ECB Working Paper Series No 2494 / November 2020 45

A.3 High, low and negative growth periods
A.3.1 In-sample RFE
Figure A.20 Optimal number of features (RFE)
0.44
F1 cross-validation score
0.42
0.40
0.38
0.36
0.34
0 500 1000 1500 2000 2500 3000 3500 4000
Table A.5 Features, high, low and negative growth periods
METLIFE Finance,InsuranceandRealEstate Hubs 1% 12m
HOMEDEPOT Retail Pagerank 1% 12m
UNUMGROUP Finance,InsuranceandRealEstate Pagerank 1% 12m
UDR Finance,InsuranceandRealEstate Out-closeness 1% 12m
UNITEDHEALTHGROUP Finance,InsuranceandRealEstate Authorities 1% 12m
SVBFINANCIALGROUP Finance,InsuranceandRealEstate Authorities 1% 12m
ECB Working Paper Series No 2494 / November 2020 46

A.3.2 Out-of-sample consistent RFE
Figure A.21 Optimal number of features (RFE)
0.30 F1 cross-validation score
0.28
0.26
0.24
0.22
0.20
0.18
0.16
0 500 1000 1500 2000 2500 3000 3500 4000
Table A.6 Features, high, low and negative growth periods
CINTAS Services Betweenness 1% 12m
METTLERTOLEDOINTL. Manufacturing Betweenness 1% 12m
JEFFERIESFINANCIALGROUP Manufacturing DegreeCentrality 1% 12m
ECOLAB Manufacturing Out-degree 1% 12m
HOMEDEPOT Retail Pagerank 1% 12m
STANLEYBLACK&DECKER Manufacturing Pagerank 1% 12m
HESS Manufacturing Pagerank 1% 12m
PINNACLEWESTCAP.

Transportation Pagerank 1% 12m
ACTIVISIONBLIZZARD Services Out-closeness 1% 12m
EQUIFAX Services In-closeness 1% 12m
TEXASINSTRUMENTS Manufacturing Authorities 1% 12m
KROGER Retail Authorities 1% 12m
ECB Working Paper Series No 2494 / November 2020 47

A.3.3 Included S&P 500 companies
@AAPL APPLE U:MS MORGANSTANLEY
@AMZN AMAZON.COM U:SLB SCHLUMBERGER
@MSFT MICROSOFT U:UPS UNITEDPARCELSER.’B’
@FB FACEBOOKCLASSA U:CVS CVSHEALTH
U:JPM JPMORGANCHASE&CO. U:NEE NEXTERAENERGY
U:JNJ JOHNSON&JOHNSON U:BLK BLACKROCK
U:XOM EXXONMOBIL @SBUX STARBUCKS
@GOOGL ALPHABETA @CHTR CHARTERCOMMS.CL.A
U:BAC BANKOFAMERICA U:DHR DANAHER
U:WMT WALMART @KHC KRAFTHEINZ
U:WFC WELLSFARGO&CO @WBA WALGREENSBOOTSALLIANCE
U:V VISA’A’ U:ANTM ANTHEM
U:PFE PFIZER U:BDX BECTONDICKINSON
U:UNH UNITEDHEALTHGROUP @BIIB BIOGEN
U:T AT&T U:SCHW CHARLESSCHWAB
U:HD HOMEDEPOT U:EOG EOGRES. U:CVX CHEVRON @ADP AUTOMATICDATAPROC.

U:MA MASTERCARD U:TJX TJX
@CSCO CISCOSYSTEMS U:AET AETNA
U:VZ VERIZONCOMMUNICATIONS U:AGN ALLERGAN
@INTC INTEL U:AMT AMERICANTOWER
U:BA BOEING U:FDX FEDEX
U:PG PROCTER&GAMBLE @MDLZ MONDELEZINTERNATIONALCL.A
U:KO COCACOLA U:PNC PNCFINL.SVS.GP. U:C CITIGROUP U:CB CHUBB
U:ORCL ORACLE U:SYK STRYKER
U:MRK MERCK&COMPANY @ATVI ACTIVISIONBLIZZARD
@CMCSA COMCASTA @CELG CELGENE
U:DIS WALTDISNEY @CSX CSX
@PEP PEPSICO @ISRG INTUITIVESURGICAL
@NFLX NETFLIX U:OXY OCCIDENTALPTL. @NVDA NVIDIA U:CL COLGATE-PALM. U:DWDP DOWDUPONT U:GD GENERALDYNAMICS
U:IBM INTERNATIONALBUS.MCHS. @CME CMEGROUP
U:ABBV ABBVIE U:RTN RAYTHEON’B’
@AMGN AMGEN U:DUK DUKEENERGY
@ADBE ADOBE(NAS) U:SPGI S&PGLOBAL
U:MDT MEDTRONIC U:SPG SIMONPROPERTYGROUP
U:MMM 3M @INTU INTUIT
U:MCD MCDONALDS @MU MICRONTECHNOLOGY
U:PM PHILIPMORRISINTL.

U:BK BANKOFNEWYORKMELLON
U:HON HONEYWELLINTL. U:BSX BOSTONSCIENTIFIC
U:ABT ABBOTTLABORATORIES @ESRX EXPRESSSCRIPTSHOLDING
U:UNP UNIONPACIFIC U:GM GENERALMOTORS
U:ACN ACCENTURECLASSA @ILMN ILLUMINA
U:MO ALTRIAGROUP U:NOC NORTHROPGRUMMAN
U:CRM SALESFORCE.COM U:PSX PHILLIPS67
U:UTX UNITEDTECHNOLOGIES U:CI CIGNA
U:LLY ELILILLY U:EMR EMERSONELECTRIC
U:NKE NIKE’B’ U:NSC NORFOLKSOUTHERN
U:GE GENERALELECTRIC U:AIG AMERICANINTL.GP. @QCOM QUALCOMM U:DE DEERE
@PYPL PAYPALHOLDINGS U:ITW ILLINOISTOOLWORKS
@TXN TEXASINSTRUMENTS U:MET METLIFE
U:BMY BRISTOLMYERSSQUIBB U:PH PARKER-HANNIFIN
@AVGO BROADCOM U:PRU PRUDENTIALFINL. @COST COSTCOWHOLESALE @FOXA FOXA
@GILD GILEADSCIENCES U:VLO VALEROENERGY
U:TMO THERMOFISHERSCIENTIFIC U:COF CAPITALONEFINL. U:AXP AMERICANEXPRESS U:CCI CROWNCASTLEINTL.

U:LMT LOCKHEEDMARTIN @MAR MARRIOTTINTL.’A’
U:CAT CATERPILLAR U:PX PRAXAIR
U:GS GOLDMANSACHSGP. @CTSH COGNIZANTTECH.SLTN.’A’
U:LOW LOWE’SCOMPANIES U:D DOMINIONENERGY
@BKNG BOOKINGHOLDINGS U:ECL ECOLAB
U:USB USBANCORP U:HCA HCAHEALTHCARE
U:COP CONOCOPHILLIPS U:HUM HUMANA
ECB Working Paper Series No 2494 / November 2020 48

U:SO SOUTHERN U:DG DOLLARGENERAL
U:TGT TARGET U:GIS GENERALMILLS
@VRTX VERTEXPHARMS. U:MCK MCKESSON
U:ICE INTERCONTINENTALEX. @ORLY OREILLYAUTOMOTIVE
U:MMC MARSH&MCLENNAN U:OKE ONEOK
U:PLD PROLOGIS U:PPG PPGINDUSTRIES
U:SHW SHERWIN-WILLIAMS U:RCL ROYALCARIBBEANCRUISES
U:ZTS ZOETIS U:YUM YUM!BRANDS
U:BAX BAXTERINTL. @ALXN ALEXIONPHARMS. U:EXC EXELON U:AVB AVALONBAYCOMMNS. U:F FORDMOTOR U:DXC DXCTECHNOLOGY
U:HPQ HP U:EQR EQUITYRESD.TST.PROPS.SHBI
@REGN REGENERONPHARMS. U:HPE HEWLETTPACKARDENTER. @AMAT APPLIEDMATS. U:HLT HILTONWORLDWIDEHDG. U:BBT BB&T U:IQV IQVIAHOLDINGS
U:DAL DELTAAIRLINES U:KR KROGER
U:KMB KIMBERLY-CLARK @LRCX LAMRESEARCH
U:KMI KINDERMORGAN @PAYX PAYCHEX
U:LYB LYONDELLBASELLINDS.CL.A U:PEG PUB.SER.ENTER.GP.

U:PGR PROGRESSIVEOHIO @TROW TROWEPRICEGROUP
U:AON AONCLASSA U:ZBH ZIMMERBIOMETHDG. U:ETN EATON U:APTV APTIV
U:IR INGERSOLL-RAND U:BBY BESTBUY
U:SYY SYSCO U:CTL CENTURYLINK
U:WM WASTEMANAGEMENT U:ED CONSOLIDATEDEDISON
U:AFL AFLAC U:CMI CUMMINS
U:APD AIRPRDS.&CHEMS. U:DLR DIGITALREALTYTST. @ADI ANALOGDEVICES U:FCX FREEPORT-MCMORAN
U:CCL CARNIVAL U:K KELLOGG
U:STZ CONSTELLATIONBRANDS’A’ U:MTB M&TBANK
@EA ELECTRONICARTS @NTRS NORTHERNTRUST
@EQIX EQUINIXREIT @PCAR PACCAR
U:FIS FIDELITYNAT.INFO.SVS. U:PCG PG&E
U:HAL HALLIBURTON U:RHT REDHAT
U:MPC MARATHONPETROLEUM U:RSG REPUBLICSVS.’A’
@ROST ROSSSTORES U:ROK ROCKWELLAUTOMATION
U:LUV SOUTHWESTAIRLINES U:SWK STANLEYBLACK&DECKER
U:VFC VF U:SYF SYNCHRONYFINANCIAL
U:ALL ALLSTATE U:TWTR TWITTER
U:AEP AMER.ELEC.PWR.

@UAL UNITEDCONTINENTALHOLDINGS
@ADSK AUTODESK U:WELL WELLTOWER
@EBAY EBAY U:WY WEYERHAEUSER
@FISV FISERV @XEL XCELENERGY
U:PSA PUBLICSTORAGE U:A AGILENTTECHS. U:STT STATESTREET @CTAS CINTAS
U:TRV TRAVELERSCOS. U:EIX EDISONINTL. U:APC ANADARKOPETROLEUM U:IP INTERNATIONALPAPER
U:EL ESTEELAUDERCOS.’A’ U:MSCI MSCI
U:JCI JOHNSONCONTROLSINTL. @NDAQ NASDAQ
@MNST MONSTERBEVERAGE @NTAP NETAPP
U:MCO MOODY’S U:COL ROCKWELLCOLLINS
U:SRE SEMPRAEN. @AAL AMERICANAIRLINESGROUP
U:STI SUNTRUSTBANKS U:AMP AMERIPRISEFINL.

U:TEL TECONNECTIVITY U:AZO AUTOZONE
U:WMB WILLIAMS @CERN CERNER
@AMD ADVANCEDMICRODEVICES U:DVN DEVONENERGY
U:EW EDWARDSLIFESCIENCES U:ES EVERSOURCEENERGY
U:ROP ROPERTECHNOLOGIES U:HES HESS
@ALGN ALIGNTECHNOLOGY U:HRL HORMELFOODS
U:ADM ARCHERDANIELSMIDLAND @IDXX IDEXXLABORATORIES
U:CNC CENTENE @INFO IHSMARKIT
U:GLW CORNING U:KEY KEYCORP
U:FTV FORTIVE U:MRO MARATHONOIL
U:PXD PIONEERNTRL.RES. U:MSI MOTOROLASOLUTIONS
U:APH AMPHENOL’A’ @MYL MYLAN
U:CXO CONCHORESOURCES U:NUE NUCOR
U:DFS DISCOVERFINANCIALSVS. U:PPL PPL
ECB Working Paper Series No 2494 / November 2020 49

U:RF REGIONSFINL.NEW U:NOV NATIONALOILWELLVARCO
U:WEC WECENERGYGROUP U:OMC OMNICOMGROUP
U:ABC AMERISOURCEBERGEN U:O REALTYINCOME
U:AME AMETEK U:RMD RESMED
U:ANET ARISTANETWORKS @SWKS SKYWORKSSOLUTIONS
U:BXP BOSTONPROPERTIES U:FTI TECHNIPFMC
U:CBS CBS’B’ @ULTA ULTABEAUTY
U:CFG CITIZENSFINANCIALGROUP U:VMC VULCANMATERIALS
U:CLX CLOROX U:WAT WATERS
@DLTR DOLLARTREE U:WCG WELLCAREHEALTHPLANS
U:DTE DTEENERGY U:ADS ALLIANCEDATASYSTEMS
@FITB FIFTHTHIRDBANCORP U:AJG ARTHURJGALLAGHER
U:FLT FLEETCORTECHNOLOGIES U:BHGE BAKERHUGHESA
U:GPN GLOBALPAYMENTS U:KMX CARMAX
U:HRS HARRIS U:CF CFINDUSTRIESHDG. @MCHP MICROCHIPTECH. @CHRW CHROBINSONWWD. U:NEM NEWMONTGOLDCORP U:CHD CHURCH&DWIGHTCO. U:TDG TRANSDIGMGROUP @CTXS CITRIXSYS.

U:VTR VENTAS U:CMS CMSENERGY
@VRSN VERISIGN U:CAG CONAGRABRANDS
@VRSK VERISKANALYTICSCL.A @ETFC ETRADEFINANCIAL
@WDC WESTERNDIGITAL U:EMN EASTMANCHEMICAL
@WLTW WILLISTOWERSWATSON U:ETR ENTERGY
U:GWW WWGRAINGER @GRMN GARMIN
@XLNX XILINX U:IT GARTNER’A’
@ABMD ABIOMED U:GPC GENUINEPARTS
U:APA APACHE @HAS HASBRO
@CA CA @INCY INCYTE
U:CAH CARDINALHEALTH U:LEN LENNAR’A’
@EXPE EXPEDIAGROUP U:MHK MOHAWKINDUSTRIES
@FAST FASTENAL U:NBL NOBLEENERGY
U:FE FIRSTENERGY U:DGX QUESTDIAGNOSTICS
U:BEN FRANKLINRESOURCES U:RJF RAYMONDJAMESFINL. U:HIG HARTFORDFINL.SVS.GP. @STX SEAGATETECH. @HBAN HUNTINGTONBCSH. U:AOS SMITH(AO)
U:LH LABORATORYCORP.OFAM.HDG. @SNPS SYNOPSYS
U:L LOEWS @TTWO TAKETWOINTACT.SFTW. @PFG PRINCIPALFINL.GP. U:TPR TAPESTRY
@SBAC SBACOMMS.

U:URI UNITEDRENTALS
@SIVB SVBFINANCIALGROUP U:VNO VORNADOREALTYTRUST
U:TXT TEXTRON U:WRK WESTROCK
U:TIF TIFFANY&CO @WYNN WYNNRESORTS
U:TSS TOTALSYSTEMSERVICES U:XYL XYLEM
U:TSN TYSONFOODS’A’ U:AAP ADV.AUTOPARTS
U:ARE ALEXANDRIARLST.EQTIES. @AKAM AKAMAITECHS. U:AEE AMEREN U:ALB ALBEMARLE
U:AWK AMERICANWATERWORKS @CDNS CADENCEDESIGNSYS. @ANSS ANSYS U:CPB CAMPBELLSOUP
U:BLL BALL U:CBOE CBOEGLOBALMARKETS
U:BR BROADRIDGEFINL.SLTN. U:CNP CENTERPOINTEN. U:BF.B BROWN-FORMAN’B’ U:CMG CHIPOTLEMEXN.GRILL
U:CBRE CBREGROUPCLASSA @CINF CINCINNATIFINL. U:CMA COMERICA U:COO COOPERCOS. U:DHI DRHORTON @CPRT COPART
U:DRI DARDENRESTAURANTS U:COTY COTYCL.A
U:EFX EQUIFAX U:DVA DAVITA
U:ESS ESSEXPROPERTYTST. U:DOV DOVER
U:EVRG EVERGY U:EQT EQT
U:FRT FEDERALREALTYINV.TST. @EXPD EXPEDITORINTL.OFWASH.

U:HSY HERSHEY @FFIV F5NETWORKS
U:HST HOSTHOTELS&RESORTS U:FMC FMC
@KLAC KLATENCOR U:HCP HCP
U:LLL L3TECHNOLOGIES @HSIC HENRYSCHEIN
U:LNC LINCOLNNATIONAL U:HFC HOLLYFRONTIER
U:MKC MCCORMICK&COMPANYNV. @JBHT HUNTJBTRANSPORTSVS. U:MTD METTLERTOLEDOINTL. U:IFF INTL.FLAVORS&FRAG. U:MGM MGMRESORTSINTL. U:SJM JMSMUCKER
ECB Working Paper Series No 2494 / November 2020 50

U:KSU KANSASCITYSOUTHERN @FLIR FLIRSYSTEMS
U:KSS KOHL’S U:FLR FLUOR
U:MLM MARTINMRTA.MATS. U:IPG INTERPUBLICGROUP
U:MAS MASCO @IPGP IPGPHOTONICS
U:MAA MID-AMER.APTCOMMUNITIES U:NI NISOURCE
U:TAP MOLSONCOORSBREWING’B’ U:PNW PINNACLEWESTCAP. U:MOS MOSAIC U:RL RALPHLAURENCL.A
U:NCLH NORWEGIANCRUISELINEHDG. U:RHI ROBERTHALFINTL. @SYMC SYMANTEC U:SLG SLGREENREALTY
U:ARNC ARCONIC U:UNM UNUMGROUP
U:AVY AVERYDENNISON U:WU WESTERNUNION
U:COG CABOTOIL&GAS’A’ U:WHR WHIRLPOOL
U:DRE DUKEREALTY U:AMG AFFILIATEDMANAGERS
U:EXR EXTRASPACESTRG. U:AIV APARTMENTINV.&MAN.’A’
U:GPS GAP U:AIZ ASSURANT
U:HII HNTGTN.INGALLSINDS. U:FLS FLOWSERVE
@HOLX HOLOGIC U:FBHS FORTUNEBNS.HM.&SCTY. U:IVZ INVESCO @GT GOODYEARTIRE&RUB. U:IRM IRONMOUNTAIN U:HBI HANESBRANDS
U:JEC JACOBSENGR.

U:HOG HARLEY-DAVIDSON
U:JNPR JUNIPERNETWORKS U:HP HELMERICH&PAYNE
U:LB LBRANDS U:JEF JEFFERIESFINANCIALGROUP
@LKQ LKQ U:KIM KIMCOREALTY
U:M MACY’S U:MAC MACERICH
@NKTR NEKTARTHERAPEUTICS U:PNR PENTAIR
U:NLSN NIELSEN U:PHM PULTEGROUP
U:JWN NORDSTROM U:SEE SEALEDAIR
U:NRG NRGENERGY U:XRX XEROX
U:PKG PACKAGINGCORP.OFAM. @BHF BRIGHTHOUSEFINANCIAL
U:PKI PERKINELMER @DISCA DISCOVERYSERIESA
U:PRGO PERRIGO U:EVHC ENVISIONHEALTHCARE
U:PVH PVH U:FL FOOTLOCKER
@QRVO QORVO U:HRB H&RBLOCK
U:SNA SNAP-ON U:LEG LEGGETT&PLATT
U:TMK TORCHMARK @MAT MATTEL
@TSCO TRACTORSUPPLY U:NFX NEWFIELDEXPLORATION
U:UDR UDR @NWSA NEWS’A’
U:UHS UNIVERSALHEALTHSVS.’B’ @PBCT PEOPLESUNITEDFINANCIAL
U:VAR VARIANMEDICALSYSTEMS U:PWR QUANTASERVICES
@VIAB VIACOM’B’ U:SCG SCANA
@ZION ZIONSBANCORP.

@SRCL STERICYCLE
U:AES AES @TRIP TRIPADVISOR’A’
U:ALK ALASKAAIRGROUP U:UAA UNDERARMOURA
U:ALLE ALLEGION @GOOG ALPHABET’C’
U:BWA BORGWARNER U:BRK.B BERKSHIREHATHAWAY’B’
U:XEC CIMAREXEN. @DISCK DISCOVERYSERIESC
@XRAY DENTSPLYSIRONA @NWS NEWS’B’
@DISH DISHNETWORK’A’ @FOX FOXB
U:RE EVERESTREGP. U:UA UNDERARMOUR’C’
ECB Working Paper Series No 2494 / November 2020 51

Acknowledgements
This study profited from discussions with Gabe de Bondt, Roberto de Santis, Lorenzo Frattarolo, Mirco Rubin and several participants of the European Commission's Joint Research Centre workshop on Big Data and Economic Forecasting in Ispra in 2019, the Modelling with Big Data and Machine Learning conference hosted by the Bank of England and King's College in London in 2019 and the Big Data/
Advanced analytics internal workshop at the European Central Bank in 2019. All remaining errors are our own. The views expressed in this paper are solely those of the authors and do not necessarily represent the views of the ECB or of the European Commission.

Andres Azqueta-Gavaldon
European Central Bank, Frankfurt am Main, Germany; University of Glasgow; email: andres.azqueta_gavaldon@ecb.europa.eu
Dominik Hirschbühl
European Central Bank, Frankfurt am Main, Germany; email: dominik.hirschbuhl@ecb.europa.eu
Luca Onorante
European Commission – Joint Research Centre, Ispra, Italy; email: luca.onorante@ec.europa.eu
Lorena Saiz
European Central Bank, Frankfurt am Main, Germany; email: lorena.saiz@ecb.europa.eu
© European Central Bank, 2020
Postal address 60640 Frankfurt am Main, Germany
Telephone +49 69 1344 0
Website www.ecb.europa.eu
All rights reserved.

Any reproduction, publication and reprint in the form of a different publication, whether printed or produced electronically, in whole or in part, is permitted only with the explicit written authorisation of the ECB or the authors. This paper can be downloaded without charge from www.ecb.europa.eu, from the Social Science Research Network electronic library or from RePEc: Research Papers in Economics. Information on all of the papers published in the ECB Working Paper Series can be found on the ECB’s website. PDF ISBN 978-92-899-4411-3 ISSN 1725-2806 doi:10.2866/23967 QB-AR-20-146-EN-N
