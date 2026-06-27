---
family: A
source: kubota2017
doc_type: pdf
reliability: 95
date: 2017
tickers: []
ingested: 2026-06-27
---

InternationalReviewofFinance,2017
DOI:10.1111/irfi.12126
Does the Fama and French FiveFactor Model Work Well in Japan?*
† ‡
KEIICHI KUBOTA AND HITOSHI TAKEHARA
†
GraduateSchoolofStrategicManagement,ChuoUniversity,Tokyo,Japanand
‡
GraduateSchoolofBusinessandFinance,WasedaUniversity,Tokyo,Japan
ABSTRACT
Inthisstudy,weinvestigatewhetherthefive-factormodelbyFamaandFrench
(2015) explains well the pricing structure of stocks with long-run data for
Japan. We conduct standard cross-section asset pricing tests and examine the additional explanatory power of the new Fama and French factors; robust-minus-weak profitability factor and conservative-minus-aggressive investment factor.

We find that robust-minus-weak and the conservativeminus-aggressive factors are not statistically significant when we conduct generalized method of moments (GMM) tests with the Hansen–Jagannathan distancemeasure.Thus,weconcludethattheoriginalversionoftheFamaand
Frenchfive-factormodelisnotthebestbenchmarkpricingmodelforJapanese dataduringoursamplingperiodfromtheyear1978totheyear2014. I. INTRODUCTION
To date, the Fama and French three-factor model has been considered adequate to explain the risk and return structure of stock data both for the USA (Fama and French 1993) and Japan (Jagannathan et al. 1998, Kubota and Takehara
2010).

However, Fama and French (2015) claim that their five-factor model is superiortotheiroriginalthree-factormodel(FamaandFrench2015)forUSfirms withnewandlongerdatafromJuly1963toDecember 2013. Thispaperexplorestheplausibilityofthisfive-factormodelproposedbyFama and French (2015) to determine whether this new model explains the long-run data of Tokyo Stock Exchange firms from January 1978 to December 2014. We duplicate the original definitions of the new two factors by Fama and French
(2015)inthecontextoffinancialstatementsdisclosedbyJapanesefirmsfollowingJapaneseGAAPandexploretheexplanatorypoweroftheirfive-factormodel when applied to Japanese data. We employ standard methodologies to choose the best asset pricing model (Hansen and Jagannathan 1997, Gibbons et al.

1989,Cochrane2005,KubotaandTakehara2015). * The authors acknowledge financial support from the Grant-in-Aid for Scientific Research ((A)
25245052)fromtheMinistryofEducation,Culture,Sports,Science,andTechnologyofJapan.Hitoshi
Takehara acknowledges financial support from the Grant-in-Aid for Scientific Research ((C)
15K03690).Allremainingerrorsareourown.

The Section II defines the five-factor model as proposed by Fama and French
(2015), and the Section III explains the data construction method. The
SectionIVreportstheresultsofassetpricingtests,andthelastsectionconcludes. II. FORMULATION OF THE FAMA AND FRENCH FIVE-FACTOR
MODEL
The Fama and French three-factor model is composed of value-weighted excess market returns (abbreviated as MKT hereafter), size-related portfolio return spreads (referred to as the SMB factor), and book-to-market ratio (B/M)-related portfolio return spreads (also known as the HML factor). The basic Fama and
Frenchthree-factormodelcanbewrittenasfollows.

(cid:1) (cid:3)
r (cid:1)r 1⁄4βM r (cid:1)r þβSMBSMB þβHMLHML þε : (1)
jt ft i Mt ft i t i t jt
Inequation((1)),r isthereturnofsecurityjinmontht,r isthereturnofthe jt Mt market portfolio, r is the risk-free rate, and SMB and HML are the Fama and ft t t
French small-minus-big and high-minus-low factors in month t, and ε is the jt errorterm. Extantliteratureshowsevidencethatthisthree-factormodelcanwellexplain the cross-sectional variation of stock returns both in the USA and in Japan. However, the theoretical background ofthe SMB and HMLfactors hasnot been provided. For this reason, Fama and French (2015) extended their three-factor model based on the dividend discount model, and, at the same time, they tried toexplainwhythebook-to-market isrelatedtostockreturns.

Let MV , d , and r denote firm j’s market value of equity, dividend, and j,t j,t E,j cost of equity capital and consider the following simple dividend discount model (2). ∞ d
MV 1⁄4 ∑(cid:1) j;tþτ (cid:3) (2)
j;t 1þr τ
1⁄41 E;j
LetY andBV denotenetincomeandbookvalueoffirmjandsupposethat j,t j,t cleansurplusrelation(3)holds. ΔBV 1⁄4BV (cid:1)BV 1⁄4Y (cid:1)d (3)
tþ1 j;tþ1 j;t j;t j;t
Then, by combining model (2) and clean surplus relation (3), we obtain the followingequation(4). ∞ (cid:1) (cid:3) (cid:1) (cid:3)
∑ Y (cid:1)ΔBV = 1þr τ
MV j;tþτ j;tþτ E;j j;t 1⁄4τ1⁄41 (4)
BV BV
j;t j;t
Thus, book-to-market is a function of future profitability (=Y j,t+τ/BV
j,t
), and investment(ΔBV j,t+τ)andprofitabilityandassetgrowthwillberelatedtoaverage stockreturns.

FamaandFrench(2015)definethemeasureofoperatingprofitability,“OP”,as annual revenues minus the cost of goods sold, interest expense, selling, and general and administrative expenses during the previous fiscal year divided by the end book value of equity. The authors also define the measure of asset growth,“INV”,asthechangeinthebookvalueoftotalassetsfromthebeginning totheendofthepreviousperioddividedbythepreviousendbookvalueoftotal assets.1Then,FamaandFrenchconstructthesizeandOP-rankedsixbenchmark portfolios at the end of June of each year and compute the robust-minus-weak
(RMW) profitability factor in a similar manner with the construction of the
HMLfactor.FamaandFrenchalsoconstructsizeandINV-rankedsixbenchmark portfolios andconservative-minus-aggressive(CMA) investmentfactors.

Adding two factors, RMW and CMA, to the three-factor model, gives the Fama and
Frenchfive-factormodelshowninequation(2). (cid:1) (cid:3)
r (cid:1)r 1⁄4 βM r (cid:1)r þβSMBSMB þβHMLHML
jt ft i Mt ft i t i t (5)
þβRMWRMW þβCMACMA þε : i t i t jt
There are other alternative multifactor models proposed by Kubota and
Takehara (1997, 2010) and Hiraki et al. (2014) for Japanese data. However, the exploration of these models is outside the scope of this short study.

Using macroeconomicvariables,analternativemultifactormodelusingtheCAPMwith humancapitalwasalsoproposedbyJagannathanandWang(1996).Theauthors demonstrate that the CAPM cannot adequately explain the risk and return structure of US stocks, and the CAPM with human capital model performs as satisfactorily as the Fama and French three-factor model (Fama and French
1993). For Japanese data, Jagannathan et al. (1998) also find that the CAPM
cannot explain the cross-sectional variations of stock returns adequately, and their CAPM withhumancapital isassatisfactoryastheFamaandFrenchthreefactormodel. Again,theinvestigation ofthis typeofmodelisoutsidethescope ofthisresearch. III.

DATA CONSTRUCTION METHOD
The source of the financial statement data was the Nikkei NEEDS Database provided by Nikkei Digital Media Incorporated. Stock returns and the market value of equity (MV) were retrieved from the NPM database provided by
FinancialDataSolutionsIncorporated.TheobservationperiodwasfromJanuary
1978 to December 2014, and we used monthly return series to measure stock returns, factor portfolio returns, and annual frequency data for financial statementdata. 1 From equation (4), OP should be based on net income and INV on book value of equity. However,wedefineOPandINVasweexplainheretomaketheempiricalresultscomparable tothoseinFamaandFrench(2015).

Forthevariable“OP”inthisstudy,weusedcurrentearningsforJapanesedata asanumeratordividedbytheendbookvalueofequityand“INV”asthechange in the book value of total assets from the beginning to the end of the previous period divided by the previous end book value of total assets. We used current earnings because the current earnings number is widely used by financial analysts in Japan, and the only difference from Fama and French (2015) is that weincludenetinterestreceived,whichshouldeventuallyaccruetostockholders. To construct Fama and French’s six benchmark portfolios and two other factors for the sample period, we used all firms listed in the first and second sections of the Tokyo Stock Exchange (TSE). The fiscal year-end for more than
90% ofthefirmslisted on theTSEistheendof March.

Accordingly, thesample firmsweresortedattheendofAugusteachyear,whichisfivemonthsaftertheir fiscal year-end, to ensure the public availability of both the number of shares issued and the book value of equity data for investors. For the firms that did not have a March fiscal year-end, we used earlier data from their financial statements.AttheendofAugustofeachyeartfrom1977through2014,allfirms listed on the TSE first and second sections were ranked by their size (=market value of equity, MV). Firms were also ranked by their BM, and the 30th and
70th percentiles of TSE first section firms were computed as data breakpoints.

Using the median MV and the 30th and 70th percentiles of BM, the firms were divided into six size and BM-ranked groups, thus allowing for the formation of six value-weighted portfolios. The Fama and French factors, MKT, SMB, and
HML were then computed by applying a method similar to that of Fama and
French(1993). The RMW factor portfolio and the CMA factor portfolio were constructed in the same way as the HML factor portfolios using the 30th and 70th percentiles ofTSEfirstsectionfirmsascomputedbydatabreakpoints. Fortherisk-freeinterestrate,themonthlyaverageoftheovernightcall-money ratewithoutcollateralasreportedbyBankofJapanwasused.

Additionally,attheendofAugustfortheyearst=1977,...,2014,firmslistedin
TSEfirstandsecondsections weresequentiallysortedbytheirsizeandBM,and
15 (=3 × 5) equally weighted portfolios were constructed.2 We also constructed size and OP-ranked 15 portfolios and size and INV-ranked 15 portfolios. Returns from these 45 portfolios (size-BM ranked 15 portfolios, size-OP ranked
15 portfolios, and size-INV ranked 15 portfolios) were used in the asset pricing testsdescribedinthenext section.3
2 Weintroducedsequentialtwo-stagesortingtoconstructthese15portfolios.Inthefirststage, weuseone-thirdsandtwo-thirdsofthemarketvalueofequityasthresholds.Then,inthesecondstage,weusethe20,40,60,and80percentileoftheBM(OPorINV)asthresholds.Asa result,almostthesamenumberoffirmsisincludedineachofthe15portfolios.

3 Cochrane(2005,p.225)recommendskeepingthenumberoftestportfoliostolessthan10%
ofthenumberofobservationsintheGMMtest.Becausewehave444monthlyobservations
(01/1978–12/2014),thenumberoftestportfolios,45inthisstudy,approximatelymeetsthat condition. We also conducted a GMM test using size and BM ranked 25(=5 × 5) portfolios; however,theconclusionisnotsubjectedtothedifferenceofthetestportfolios.

IV. FACTOR RETURNS FOR JAPANESE DATAAND ASSET PRICING
TESTS
Before exploring the behavior of the five-factor model in Japan, we report the average returns from the 45 portfolios (size-BM ranked 15 portfolios, size-OP
ranked 15 portfolios, and size-INV ranked 15 portfolios), which are used as dependent variables in asset pricing tests, to investigate the “operating profit effects”and“assetgrowtheffects”inJapan. Fama and French (1993) write that “The bottom-line results in that two empirically determined variables, size and book-to-market equity do a good job explaining the cross-section of average returns on NYSE, Amex, and NASDAQ stocks for the 1963–1990 period.” (Fama and French 1993, p. 4).

Thus, we first go back to Fama and French (1992) and examine whether the two new characteristics,
OPandINV,canexplainthecross-sectionalreturnvariationsofJapanesestocks. Table 1 reports the average monthly realized returns from the 45 portfolios. First, we reconfirm the existence of strong “value effects” in Japan. For largeand medium-sized stocks, return spreads (P1–P5) are very high at 0.700 and
0.826% per month, and they are statistically significant at the 5% level. By contrast,OPseemsunrelatedtothestockreturns.Weobservenocleartendency betweenOPandstockreturnsinTable1,andthemagnitudeofreturnspreadsare relatively small and not significant without exception. Finally, as for firms’
Table1 Averagereturnsfrom45portfolios
SizeandB/Mranked15portfolios
P1(High) P2 P3 P4 P5(Low) Diff.

p-Value
Large 2.023 1.848 1.719 1.438 1.324 0.700 0.036
Mid. 2.281 1.924 1.881 1.903 1.455 0.826 0.004
Small 2.698 2.678 2.567 2.585 2.436 0.262 0.345
SizeandOPranked15portfolios
P1(Robust) P2 P3 P4 P5(Weak) Diff. p-Value
Large 1.735 1.640 1.560 1.513 1.900 (cid:1)0.165 0.508
Mid. 1.792 1.955 1.906 1.805 1.983 (cid:1)0.191 0.300
Small 2.623 2.311 2.413 2.732 2.886 (cid:1)0.263 0.173
SizeandInvranked15portfolios
P1(Aggressive) P2 P3 P4 P5(Conservative) Diff. p-Value
Large 1.374 1.571 1.725 1.775 1.905 (cid:1)0.531 0.123
Mid. 1.586 1.810 1.843 1.967 2.237 (cid:1)0.652 0.013
Small 2.333 2.460 2.501 2.885 2.788 (cid:1)0.455 0.017
Average monthly returns of size-B/M, size-OP, and Size-INV ranked 15 portfolios.

Numbers in column“Diff.”areaveragereturnspreads(P1–P5),andtheircorrespondingprobabilityvaluesin
Welch’s two-sample t-testare reported incolumn“p-value.”The sampleperiodis fromJanuary
1978toDecember2014.

investments (INV), they are negatively related to stock returns, as Fama and
French expected. However, we can expect only limited effects on the stock market as the return spreads are significant only in medium and small capital categories.Toputitmoresuccinctly,thetwonewvariables,OPandINV,cannot explainthecross-sectionalvariationofJapanesestock.Thus,thevaliditiesofthe
RMWandCMAfactorsconstructedusingOPandINVarequestionable. Table 2 reports the basic statistics of the factors we used for the final factor model tests with four and five-factor models. In Panel A, we report the basic statistics, and, in Panel B, we report the correlation numbers among these candidate five factors. The observation period of our monthly data was January
1978 through December 2014.

The numbers reported are in percentages, and fortheexcessmarketreturn,MKT,theaveragemonthlyreturnis0.314%,which is equivalent to 3.768% per annum. All the factor returns have positive average valuesexcepttheoperatingprofitfactor,RMW,with(cid:1)0.088%.Forthestandard deviation,MKTshowsthehighestvariability.Wealsoreportthe25thpercentile, themedian,andthe75thpercentilefiguresintheright-handfourcolumns.For themedian,we find thattheRMW factorispositive in contrast withthemean. Otherwise, the differences between the means and medians are not substantial. Panel B reports the correlation numbers between the five factors.

The lower-left
Table2 DescriptivestatisticsoftheFamaandFrenchfivefactormodel
PanelA.Summarystatistics
Mean (p-Value) SD 25%ile Median 75%ile
MKT 0.314 0.197 5.152 (cid:1)2.476 0.390 3.535
SMB 0.083 0.603 3.382 (cid:1)1.802 0.153 2.186
HML 0.583 0.000 2.978 (cid:1)0.911 0.418 2.044
RMW (cid:1)0.088 0.364 2.051 (cid:1)1.287 0.007 1.011
CMA 0.128 0.263 2.413 (cid:1)1.087 0.160 1.345
PanelB.CorrelationmatrixamongtheFamaandFrenchfivefactors
MKT SMB HML RMW CMA
PRC1 (cid:1)0.803 (cid:1)0.423 (cid:1)0.127 0.107 0.107
PRC2 (cid:1)0.174 0.160 0.304 0.322 0.436
PRC3 (cid:1)0.416 0.581 0.143 (cid:1)0.223 (cid:1)0.105
PRC4 (cid:1)0.073 0.347 (cid:1)0.052 (cid:1)0.029 0.123
PRC5 (cid:1)0.011 (cid:1)0.068 (cid:1)0.059 0.074 0.160
PRC6 (cid:1)0.181 0.269 0.024 (cid:1)0.238 0.104
PRC7 0.070 (cid:1)0.116 0.019 (cid:1)0.098 0.012
MKT,excessreturnsfromthevalue-weightedmarketindex;SMB,small-minus-bigfactor;HML, high-minus-low factor; RMW, robust-minus-weak factor; CMA, conservative-minus-aggressive factor.“Mean”isanarithmeticaverageofmonthlyreturnfromfactors(in%),and“p-value”isa probabilityvaluefromStudent’st-testinwhichthenullhypothesisisthearithmeticaverageof the risk factor equal to zero.

“SD” is a standard deviation of risk factors. “25%ile,”, “median,”
and“75%ile”denotethe25percentile,median,and75percentileofriskfactors,respectively.In
Panel B, Pearson correlations among the five factors are shown in the lower-left triangularpart ofthematrix,andSpearmanrankcorrelationsareshownintheupper-righttriangularpart.

triangular part reports Pearson correlations, and we find CMA is positively correlated with HML at 0.384 and RMW is negatively correlated with HML
at(cid:1)0.240. Table 3 reports the correlation between the five factors and the first seven principalcomponentsestimatedfromthereturnsofindividualsecuritieslistedduringtheobservationperiodfromtheyear1978totheyear2014.Wefindthatthe firstprincipal componenthas highcorrelationswith MKT at(cid:1)0.803and SMB at
(cid:1)0.423. The second principal component is correlated with CMA and RMW at
0.436 and 0.322, respectively.

The third principal component is correlated with
SMBandMKTat0.581and(cid:1)0.414,respectively.Thefourthprincipalcomponent iscorrelatedwithSMBat0.347.However,surprisingly,theHMLfactorisnothighly correlatedwithprincipalcomponentsexceptforthesecondprincipalcomponent at0.304,whichisalsocorrelatedwithCMAandRMW. Table4reportstheresultsfromFama&MacBeth(1973)regressionsinwhich wetestthefollowingmulti-betamodel(6).

r (cid:1)r 1⁄4γ þγ βMKT þγ βSMBþγ βHMLþγ βRMW þγ βCMAþε: (6)
j f 0 1 j 2 j 3 j 4 j 5 j j
Table3 Correlationbetweenstatisticalfactorsandthefivefactormodel
MKT SMB HML RMW CMA
PRC1 (cid:1)0.803 (cid:1)0.423 (cid:1)0.127 0.107 0.107
PRC2 (cid:1)0.174 0.160 0.304 0.322 0.436
PRC3 (cid:1)0.416 0.581 0.143 (cid:1)0.223 (cid:1)0.105
PRC4 (cid:1)0.073 0.347 (cid:1)0.052 (cid:1)0.029 0.123
PRC5 (cid:1)0.011 (cid:1)0.068 (cid:1)0.059 0.074 0.160
PRC6 (cid:1)0.181 0.269 0.024 (cid:1)0.238 0.104
PRC7 0.070 (cid:1)0.116 0.019 (cid:1)0.098 0.012
MKT,excessreturnsfromthevalue-weightedmarketindex;SMB,small-minus-bigfactor;HML, high-minus-low factor; RMW, robust-minus-weak factor; CMA, conservative-minus-aggressive factor.PRC1throughPRC7arethefirstsevenprincipalcomponentscomputedusingthereturns ofindividualsecuritiesfromJanuary1978throughDecember2014.

Table4 ResultsofFamaandMacBethregressions
(1) (2) (3) (4)
Intercept(γ0) 1.381*** 0.300 0.501 0.338
MKT(γ1) (cid:1)0.769* 0.110 0.001 (cid:1)0.009
SMB(γ2) 0.152 0.487** 0.110
HML(γ3) 0.819*** 1.151***
RMW(γ4) 0.021 0.216
CMA(γ5) 0.529*** (cid:1)0.294
AdjustedR2 0.023 0.806 0.678 0.828
γ ,γ ,γ ,γ ,γ ,andγ areestimatedriskpremiumforbetas.ThesampleperiodisfromJanuary1978
0 1 2 3 4 5
throughDecember2014(444months).Thedependentvariablesarereturnsfrom45testportfolios
(whicharebasedonSize-B/Mranked15,Size-OPranked15,andSize-INVranked15portfolios). ***Significantat1%.**Significantat5%.*Significantat10%.

The test reveals the factors that are priced among candidate five factors and reports the overall fitness of the model. The MKT is not significant except for the CAPM and the coefficient is negative. However, the evidence is consistent with previous evidence on TSE firms (Jagannathan et al. 1998). The HML beta is significant with positive coefficients for the Fama and French three-factor andfive-factormodel.However,thecoefficientsontheSMBbetaareallpositive whilesignificantonlyforthefour-factormodelinwhichtheHMLbetaisreplaced byRMWandCMAbetas.Wereporttheresultsfromthisfour-factormodelbecause
FamaandFrench(2015)findthatthisfour-factormodelperformsaswellastheir five-factormodel,andweattempttoconfirmthatthisistrueforJapanesedataalso.

ThesignificanceoftheSMBfactor,however,canbefoundonlyforthisfourfactor model,andtheoverallHMLbetaisrobustinexplainingthecrosssectionofstock returns for Japan. After dropping the HML beta, SMB beta re-emerges again as a strong explanatory variable because the other two factors, RMW and CMA, are notstrongexplanatoryvariablesjudgingfromthedecreaseinadjustedR-squared valuesto0.678,whilethecoefficientforCMAissignificant.Forfive-factormodels, however,thesenewtwofactorsarenotsignificantandthesignoftheslopeforthe
CMAbetachangestoanincorrectnegativesign. Table 5 reports the results from a GMM test in which we test the Euler condition (7).

(cid:4)(cid:1) (cid:3)(cid:1) (cid:1) (cid:3) (cid:3)(cid:5)
E r (cid:1)r (cid:3) 1þδ r (cid:1)r þδ SMB þδ HML þδ RMW þδ CMA 1⁄40: (7)
p;t f;t 1 M;t f;t 2 t 3 t 4 t 5 t
In the above pricing equation (7), we judge the fitness of the model with
Hansen and Jagannathan distance measure (Hansen and Jagannathan 1997). For the distance measures, the Fama and French five-factor model shows the shortest distance at 0.345. Hansen–Jagannathan distance for the Fama and
French three-factor model is 0.346, which is much smaller than that of the four-factormodelat0.396forwhichHMLisdroppedfromthefive-factormodel. ContrarytothecaseforUSdata,wefindthatthefour-factormodelisinferiorto thethree-factormodel,andHMLisnotaredundantfactorinJapan.

Table5 ResultsofGMMtests
(1) (2) (3) (4)
MKT(δ1) (cid:1)1.412 (cid:1)2.022** (cid:1)1.951** (cid:1)1.932**
SMB(δ2) 0.220 (cid:1)0.582 0.350
HML(δ3) (cid:1)8.052*** (cid:1)8.316***
RMW(δ4) 3.030 0.751
CMA(δ5) (cid:1)4.268* 1.034
HJ-Dist 0.410*** 0.346* 0.396*** 0.345**
Inthetable,δ ,δ ,δ ,δ ,andδ aretheparametervaluesinequation(7)ofthemaintext.“HJ-Dist”
1 2 3 4 5
denotestheHansen–Jagannathandistancemeasure.Thesignificancelevelofthecoefficientsand the significance level of the Hansen and Jagannathan distance measure for the GMM test are showninthetable.IntheGMMtest,T=444,N=45,andK=1,3,4,5.Thep-valuesarecomputed by numerically generating χ2(1) values 10,000 times. ***Significant at 1%. **Significant at 5%. *Significantat10%.

Table6 ResultsofGibbons–Ross–Shankentests
Model CAPM Three-factormodel Four-factormodel Five-factormodel
Factors MKT MKT+SMB+HML MKT+SMB+ FF3+RMW+CMA
RMW+CMA
GRSF-value 10.064 9.491 9.988 9.447
p-Value 0.000 0.000 0.000 0.000
GRS F-value denotes Gibbons–Ross–Shanken (1989)’s test statistic for mean–variance efficiency, andthep-valuedenotesitscorrespondingprobabilityvalues. For the three-factor model, the MKT and HML coefficients show correct negative signs (Jagannathan and Wang 1996). For the four-factor model, CMA
is significant at the 10% level and, for the five-factor model, HML is significant at the 1% level, thus deleting the significance of RMW and CMA factors. Null hypothesisofzeropricingerrorisrejectedinallcandidatemodels.

Table6reportstheresultsfromtheGibbons–Ross–Shakentest(Gibbonsetal. 1989).Wefindallcandidatemodelsarerejectedinthismean–varianceefficiency test as was the case in Fama and French (2015) for US data. However, the test statistic is at the minimum for the Fama and French five-factor model at 9.447, and the three-factor model was the next best at 9.491, which implies that the simpler three-factor model functions at a similar level as the five-factor model. The test statistic of the four-factor model is high at 9.988, and it is at almost the same level as that of the CAPM at 10.064.

Although the four-factor model is suitable for the USA and functions as well as the five-factor model (Fama and
French 2015), we conclude the performance of the four and five-factor models are inferior to the three-factor model for Japanese data in terms of model simplicityandsignificanceofthecoefficients. V.

CONCLUSIONS
We investigated whether the five-factor model by Fama and French (2015) can adequatelyexplainthepricingstructureoflong-runstockdataforJapan.Wefind that the historical averages of these new two factors are not large and are statistically insignificant, which is contrary to the evidence for the US by Fama andFrench(2015).Fromtheassetpricingtests,wefindthatboththeRMWbetas and the CMA betas are weakly associated with the cross-sectional variations of stock returns, which is significantly different from the US evidence. Finally, we demonstrate that the coefficients of these two factors are not statistically significant when we conduct GMM tests with the Hansen and Jagannathan distancemeasure.

Weconclude thattheFamaandFrenchfive-factormodel, ortheir four-factor model,whichfitsUSdata,cannotbeanadequatebenchmarkpricingmodel for
Japanese data during our sampling period from the year 1978 to the year 2014. Furtherout-of-sampletests,asinLewellen(2015),aresubjectsforfutureresearch.

HitoshiTakehara
GraduateSchoolofBusinessandFinance
WasedaUniversity
1-6-1Shinjyuku-ku
Tokyo169-8050
Japan takehara@waseda.jp
REFERENCES
Cochrane, J. (2005), Asset Pricing, Revised Edn. Princeton, NJ: Princeton University
Press. Fama,E.F.,andK.R.French(1993),‘CommonRiskFactorsintheReturnsonStockand
Bonds’,JournalofFinancialEconomics,33(1),3–56. Fama, E. F., and K. R. French (2015), ‘A Five-Factor Asset Pricing Model’, Journal of
FinancialEconomics,116(1),1–22. Fama, E. F., and J. MacBeth (1973), ‘Risk, Return, and Equilibrium: Empirical Tests’,
JournalofPoliticalEconomy,81(3),607–36. Gibbons, M., S. Ross, and J. Shanken (1989), ‘A Test of the Efficiency of a Given
Portfolio’,Econometrica,57(5),1121–52.

Hansen,L.P.,andR.Jagannathan(1997),‘AssessingSpecificationErrorsinStochastic
DiscountFactorModels’,JournalofFinance,52(1),557–90. Hiraki,T.,WatanabeA.,andWatanabeM.(2014).‘TheInvestmentValueofEarnings
Forecasts’,SSRNWorkingPaper,Abstract=id1989896. Jagannathan, R., K. Kubota, and H. Takehara (1998), ‘Relationship between Labor–
Income Risk and Average Return: Empirical Evidence from the Japanese Stock
Market’,JournalofBusiness,71(1),319–47. Jagannathan,R.,andZ.Wang(1996),‘TheConditionalCAPMandtheCross-Sectionof
ExpectedReturns’,JournalofFinance,51(1),3–53. Kubota, K., and H. Takehara (1997), ‘Common Risk Factors of Tokyo Stock Exchange
Firms: Finding Mimicking Portfolios’, in T. Boss and T.

Fetherston (eds), Advances inPacificBasinFinancialMarkets,Vol.3.Greenwich,CT:JAIPress,Inc.,pp.273–302. Kubota, K., and H. Takehara (2010), ‘Expected Return, Liquidity Risk, and Contrarian
Strategy: Evidence from the Tokyo Stock Exchange’, Managerial Finance, 36(8),
655–79. Kubota, K., and H. Takehara (2015), Reform and Price Discovery at the Tokyo Stock
Exchange:From1990to2012.NYC,NY:Palgrave-Macmillan. Lewellen, J. (2015), ‘The Cross Section of Expected Stock Returns’, Critical Finance
Review,4(1),1–44.
