---
family: A
source: fama2015
doc_type: pdf
reliability: 95
date: 2015
tickers: []
ingested: 2026-06-27
---

Dissecting Anomalies with a Five-Factor
Model
EugeneF.Fama
BoothSchoolofBusiness,UniversityofChicago
KennethR.French
AmosTuckSchoolofBusiness,DartmouthCollege
Afive-factormodelthataddsprofitability(RMW)andinvestment(CMA)factorstothe three-factormodelofFamaandFrench(1993)suggestsasharedstoryforseveralaveragereturnanomalies.Specifically,positiveexposurestoRMW andCMA(stockreturnsthat behavelikethoseofprofitablefirmsthatinvestconservatively)capturethehighaverage returnsassociatedwithlowmarketβ,sharerepurchases,andlowstockreturnvolatility. Conversely,negativeRMWandCMAslopes(likethoseofrelativelyunprofitablefirmsthat investaggressively)helpexplainthelowaveragestockreturnsassociatedwithhighβ,large shareissues,andhighlyvolatilereturns.

(JELG1,G11,G12)
ReceivedNovember11,2014;acceptedApril27,2015byEditorAndrewKarolyi. Motivated by the dividend discount valuation model, Fama and French
(FF; 2015) add profitability and investment factors to the market, Size, and value/growthfactorsofthethree-factormodelofFamaandFrench(FF;1993). In FF (2015) the left-hand-side (LHS) assets used to test the resulting fivefactormodelareportfoliosformedusingsortsonSize(marketcapitalizationor marketcap)andcombinationsofthebook-to-marketequityratio,profitability, and investment.The LHS portfolios are thus just finer sorts on the variables usedtoconstructthefactors.

Here we follow the advice of Lewellen, Nagel, and Shanken (2010) and consideranomaliesnottargetedbythefive-factormodelandknowntocause problemsfortheFFthree-factormodel.Accruals(Sloan1996),netshareissues
(Ikenberry, Lakonishok, and Vermaelen 1995; Loughran and Ritter 1995), momentum(JegadeeshandTitman1993),andvolatility(Angetal.2006)are prominentexamples.Thereisalsolong-standingevidence(Black,Jensen,and
Scholes 1972; Fama and MacBeth 1973) that the relation between average return and market β is flatter than predicted by the Sharpe (1964)-Lintner
TheauthorsthankSavinaRizovaforconstructingthedatafilesandAndrewKarolyi(theeditor)andtworeferees forcommentsthatsubstantiallyimprovedthepaper.E.F.F.andK.R.F.areconsultantsto,boardmembers of,andshareholdersinDimensionalFundAdvisors.SendcorrespondencetoKennethR.French,Dartmouth
College,Hanover,NH03755;telephone:603-643-5750.E-mail:kfrench@dartmouth.edu.

©TheAuthor2015.PublishedbyOxfordUniversityPressonbehalfofTheSocietyforFinancialStudies. Allrightsreserved.ForPermissions,pleasee-mail:journals.permissions@oup.com. doi:10.1093/rfs/hhv043 AdvanceAccesspublicationAugust10,2015
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

(1965)CAPM.Thegoalhereistoexaminewhetherthefive-factormodeland modelsthatusesubsetsofitsfactorscaptureaveragereturnsfromsortsonthese variables and whether portfolios that signal model problems have exposures to the size, profitability, and investment factors typical of stocks that cause problemsforthefive-factormodelinmanysortsinFF(2015). Giventhelargenumberofanomaliesresearchershavediscoveredinstock returns,onemightaskwhytheadditionstotheFF(1993)three-factormodel areprofitabilityandinvestmentfactors.FF(2015)arguethatthesearenatural choices, suggested by the dividend discount model. Miller and Modigliani
(1961)showthatinthedividenddiscountmodel,M t,thetimet marketcapof afirm’sstock,is,
(cid:2)∞
M t= E(Y t+τ −dB t+τ)/(1+r) τ.

(1)
τ=1
Inthisequation,Y t+τisequityearningsforperiodt+τ,dB
t+τ
≡B
t+τ
−B
t+τ−1
isthechangeinbookequity,andr,theinternalrateofreturnonexpectedcash flows to shareholders, is approximately the long-term expected stock return. Dividingbytimet bookequitygives
(cid:3)∞
M
E(Y
t+τ
−dB t+τ)/(1+r)τ
t
=
τ=1
(2)
B B
t t
Equation(2)impliesthatifweholdconstanteverythingexceptthecurrent value of the stock, M t, and the expected stock return, r, a lower value of
M t, or equivalently a higher book-to-market equity ratio, B t /M t, implies a higherexpectedreturn.Similarly,ifweholdM t,B t,andthestreamoffuture investments(dB t+τ)fixed,higherexpectedprofitabilityimplieshigherexpected cash flows to shareholders and a higher expected stock return.

Finally, given
M t,B t,andthestreamoffutureearnings,higherexpectedinvestmentimplies lower expected cash flows and a lower expected return. In short, (2) implies
B t /M t is a noisy proxy for expected return because the market cap M t also respondstoforecastsofearningsandinvestment. Mostofourtestsusevariantsofthefive-factortime-seriesregression
R
−R Ft=a i+b i(R
−R Ft)+s iSMBt+h iHMLt+r iRMWt+c iCMAt+e
. (3)
InthisequationR it isthemontht returnononeoftheportfoliosfromsorts ofstocksonSizeandananomalyvariable,R Ft istherisk-freerate(theonemonth U.S.

Treasury-bill rate observed at the beginning of month t), R Mt is the return on the value-weight (VW) portfolio of NYSE-AMEX-NASDAQ
stocks,SMBt (smallminusbig)andHMLt (highminuslowB/M)aretheSize andvaluefactorsoftheFFthree-factormodel,RMWt (robustminusweak)isa profitabilityfactor,andCMAt(conservativeminusaggressive)isaninvestment factor. Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

The bottom line from our tests is that the list of anomalies shrinks when we use the five-factor model, in part because anomaly returns become less anomalousandinpartbecausethereturnsfordifferentanomalieshavesimilar five-factor exposures (regression slopes in (3)) that suggest they are related phenomena. With two exceptions, accruals and momentum, the five-factor modelshrinksanomalyaveragereturnsleftunexplainedbytheFFthree-factor model.Moreover,thesuccessesandfailuresofthemodelarelinkedtopatterns intheslopesforRMWt andCMAt thatarecommontothesortsonβ,netshare issues, and volatility.

The high average returns associated with low β, share repurchases, and low volatility that are left unexplained by the three-factor model are absorbed by positive five-factor exposures to RMWt and CMAt, typicalofprofitablefirmsthatinvestconservatively.Attheotherextreme,the lowaveragereturnsassociatedwithhighβ,largeshareissues,andhighreturn volatilitythatareleftunexplainedbythethree-factormodelaresubstantially capturedbynegativefive-factorexposurestoRMWt andCMAt,typicalofless profitablefirmsthatinvestaggressively.

In the sorts on net share issues and volatility, the portfolios that cause the most serious problems for the five-factor model are in the smaller Size quintilesandthehighestquintilesofshareissuesandvolatility.Theseportfolios have negative exposures to RMWt and CMAt that lower estimates of their expected returns, but not enough to explain their low average returns. Most interesting,thecommonpatternsinthefive-factorslopesfortheseportfolios suggest they share the lethal traits—small stocks whose returns behave like thoseofrelativelyunprofitablefirmsthatinvestaggressively—thatplaguethe five-factormodelinFF(2015). Accrualsposespecialproblems.Forotheranomalies,thefive-factormodel improvesthedescriptionofaveragereturnsoftheFFthree-factormodel.For accruals the five-factor model does worse.

The problem is that in the sorts onaccruals,portfoliosinthesmallestSizequintile(microcaps)havenegative
RMWt slopes but they do not have the predicted low average returns. Hou,
Xue,andZhang(2015)alsofindthatsortsonaccrualsproduceaveragereturns thatescapeexplanationbyamodelsimilartoours. For the anomalies discussed above, adding a momentum factor to the five-factor model has little effect on performance, simply because the sorts do not produce portfolios with large momentum tilts. For portfolios formed on momentum, however, the five-factor model does poorly, with regression intercepts about as disperse as average returns on the portfolios. Adding a momentum factor improves model performance, but leaves nontrivial unexplainedmomentumreturnsamongsmallstocks. 1.

TheFactors
Droppingthetimesubscriptonthevariables,thetestsofthefive-factormodel usetheR M −R F,SMB,andHMLfactorsofthethree-factormodelofFF(1993),
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table1
Averages,standarddeviations,andt-statisticsformonthlyfactorreturns,July1963–December2014(618
months)
RM-RF SMB HML RMW CMA MOM
Mean 0.51 0.27 0.36 0.25 0.32 0.69
SD 4.46 3.07 2.86 2.14 1.99 4.22
t-statistic 2.83 2.20 3.15 2.88 4.04 4.05
RM−RF isthevalue-weightreturnonthemarketportfolioofallsamplestocksminustheone-monthTreasury billrate.AttheendofeachJune,NYSE,AMEX,andNASDAQstocksareallocatedtotwoSizegroups(smalland big)usingtheNYSEmedianmarket-capbreakpoints.StocksareallocatedindependentlytothreeB/Mgroups
(lowtohigh),usingNYSE30thand70thpercentilebreakpoints.Theintersectionsofthetwosortsproducesix value-weightSize-B/Mportfolios.InthesortforJuneofyeart,Bisbookequityattheendofthefiscalyear endinginyeart−1andMismarketcapattheendofDecemberofyeart−1,adjustedforchangesinshares outstandingbetweenthemeasurementofBandtheendofDecember.WeuseCompustatdatatocomputebook equity,definedas(1)stockholdersequity(ortheparvalueofpreferredplustotalcommonequityorassetsminus liabilities,inthatorder)minus(2)theredemption,liquidation,orparvalueofpreferred(inthatorder)plus(3)
balancesheetdeferredtaxes,ifavailable,minus(4)postretirementbenefits,ifavailable.Wefillinmissingbook equitydataforNYSEstocksasinDavis,Fama,andFrench(2000).HMListheaverageofthereturnsonthe twohighB/Mportfoliosfromthe2×3sortsminustheaverageofthereturnsonthetwolowB/Mportfolios.

Theprofitabilityandinvestmentfactors,RMW(robustminusweak)andCMA(conservativeminusaggressive), areformedinthesamewayasHML,exceptthesecondsortvariableisoperatingprofitabilityorinvestment.

Operatingprofitability,OP,inthesortforJuneofyeartismeasuredwithaccountingdataforthefiscalyear endinginyeart−1andisrevenueminusthecostofgoodssold,minusselling,general,andadministrative expenses,minusinterestexpense,alldividedbybookequity.Investment,Inv,isthechangeintotalassetsfrom thefiscalyearendinginyeart−2tothefiscalyearendingint−1,dividedbyt−2totalassets.Intheseparate
Size-B/M,Size-OP,andSize-Invsorts,therearethreeversionsofSMB,oneforeach2×3sort,andSMBisthe averageofthethree,orequivalently,itistheaverageofthereturnsontheninesmallstockportfoliosfrom thethreesortsminustheaverageoftheninebigstockportfolios.Themomentumfactor,MOM,isdefinedinthe samewayasHML,exceptthefactorisupdatedmonthlyratherthanannually.ToformthesixSize-Prior2−12
portfoliosattheendofmontht−1,Sizeisthemarketcapofastockattheendoft−1andPrior2−12isits cumulativereturnforthe11monthsfromt−12tot−2.Thetableshowsaveragemonthlyreturns(mean),the standarddeviationsofmonthlyreturns(SD),andthet-statisticsfortheaveragereturns.

augmentedwithsimilarprofitabilityandinvestmentfactors.TheSMBandHML
factorsoftheoriginalmodeluseindependentsortsofstocksintotwoSizegroups andthreebook-to-marketequity(B/M)groups(independent2×3sorts).The
Size breakpoint is the NYSE median market cap, and the B/M breakpoints arethe30thand70thpercentilesofB/M forNYSEstocks.Theintersections ofthesortsproducesixVWportfolios.TheSizefactorSMBBM istheaverage of the three small stock portfolio returns minus the average of the three big stock portfolio returns.The value factor HML is the average of the two high
B/MportfolioreturnsminustheaverageofthetwolowB/Mportfolioreturns.

The profitability and investment factors, RMW and CMA, are constructed in the same way as HML, except the second sort is on operating profitability
(OP)orinvestment(Inv).Definitionsofthesortvariablesanddetailsoffactor constructionareinTable1. The 2×3 sorts used to construct RMW and CMA produce two additional
Sizefactors:SMB
OP
andSMBInv.TheSizefactorSMBusedinthetestsisthe averageofthereturnsontheninesmallstockportfoliosofthethree2×3sorts minustheaverageofthereturnsontheninebigstockportfolios. Nocombinationofthefactorsin(3)explainsaveragereturnsonportfolios formed on momentum. Thus, in the tests in which the LHS asset returns to be explained are for momentum portfolios, we include a momentum factor,
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

MOM,amongtheright-hand-side(RHS)explanatoryreturns.MOMisdefined likeHML,exceptthatitisupdatedmonthlyratherthanannually,andthesortfor portfoliosformedattheendofmontht−1isbasedonthecumulativeaverage returnsfromt–12tot–2,calledPrior2–12.NotethatMOM isreconstituted monthly using the most recently available data, whereas SMB, HML, RMW, andCMAareupdatedannuallyusingdatathat,exceptforSize,areatleastsix monthsold.(SeeTable1.)
Oursampleisthe618monthsfromJuly1963toDecember2014(henceforth
1963–2014). The average monthly returns on the factors for this period are all more than two standard errors above zero (Table 1). The average equity premium(R M −R F)for1963–2014islarge,0.51%permonth,butthemonthly standarddeviationisalsosubstantial,4.46%,andthet-statisticfortheaverage premium is 2.83.

The average HML return has a larger t-statistic, 3.15, the result of combining a smaller average premium, 0.36% per month, with a smallerstandarddeviation,2.86%.Theprofitabilityfactor,RMW,hasthelowest averagepremium,0.25%permonth,butbecauseofitslowstandarddeviation,
2.14%,itst-statisticis2.88.Theinvestmentandmomentumfactors,CMAand
MOM,havethelargestt-statistics,4.04and4.05.Thelarget-statisticforCMA
combinesamoderatefactorpremiumof0.32%permonthwiththelowestfactor standarddeviation,1.99%.Incontrast,thelarget-statisticforMOMcombines thesecondhigheststandarddeviation,4.22%,withthehighestaveragereturn,
0.69%permonth.FF(2015)providemoredetailonfactorconstructionandthe behavioroffactorreturns.

The momentum factor plays a critical role when the LHS returns in asset pricingregressionsareformomentumportfolios.ButincludingMOMproduces smallchangesinmodelperformancewhentheLHSportfolios(hereandinFF
2015)arenotformedonmomentum.Thus,weputthemomentumfactoraside exceptwhenweaddressthemomentumanomaly.Wehavealsotriedmodelsthat addtheliquidityfactorofPástorandStambaugh(2003)todifferentversions of regression (3). Skipping the details, the portfolios examined here (and in
FF 2015) have trivial loadings on the traded and nontraded versions of the liquidityfactor,andincludingthetradedversionproducesonlytinychangesin regressionintercepts. 2.

SummaryAssetPricingTests
Weturnnowtoourcentraltask:examininghowwellvariantsofthefive-factor model capture average returns on portfolios formed on Size and each of the anomaly variables.Two-way sorts on Size and an anomaly variable allow us to see how anomaly returns, and explanations of them provided by different models, vary across Size groups. This section presents summary tests. Later sectionsexamineregressioninterceptsandpertinentslopesforeachanomaly variable.Webeginbyintroducingtheleft-hand-sideportfoliosinthetests. Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

2.1 TheLHSanomalyportfolios
2.1.1Marketβ. Manystudies,fromBlack,Jensen,andScholes(1972)and
FamaandMacBeth(1973)toFrazziniandPedersen(2014)findthattherelation betweenunivariatemarketβandaveragestockreturnisflatterthanpredictedby theCAPMofSharpe(1964)andLintner(1965).Weconstruct25VWportfolios attheendofJuneeachyearfromindependentsortsofstocksintoquintilesof
SizeattheendofJuneandβestimatedusingtheprecedingfiveyears(twoyears minimum)ofpastmonthlyreturns.Asinalloursorts,thequintilebreakpoints useNYSEstocks,butthesampleisNYSE,AMEX,andNASDAQstockson both CRSP and Compustat with data for the variables in the sort and share codes10or11.Forabitofcolor,stocksinthebottomandtopSizequintiles areoftencalledmicrocapsandmegacaps. 2.1.2 Net share issues.

Share repurchases tend to be followed by large average returns (Ikenberry, Lakonishok, and Vermaelen 1995), and average returnsaftershareissuestendtobelow(LoughranandRitter1995).Weform
35 portfolios from independent sorts of stocks into Size quintiles and seven net share issues (NI) groups. Portfolio formation follows the same rules as theSize-β sorts,exceptthesecondsortisonNI andtherearesevengroups—
negativeNI(netrepurchases),zeroNI,andquintilesofpositiveNI(netissues). Thechoiceofonerepurchasegroupisabitarbitrarybutinlinewiththefact that net repurchases are less frequent than net issues, and for big stocks a finer breakdown of repurchases would produce undiversified portfolios.

For portfolios formed in June of year t, NI is the change in the natural log of split-adjustedsharesoutstandingfromthefiscalyear-endint−2tothefiscal year-endint−1. 2.1.3 Volatility. Ang et al. (2006) find that stocks with highly volatile returns tend to have low average returns whether volatility is measured as the variance of daily returns or as the variance of the residuals from the FF
three-factor model.

We construct VW portfolios using monthly sorts on Size andVarorSizeandRVar,whereVaristhevarianceofdailyreturns,andRVaris thevarianceofdailyresidualsfromtheFFthree-factormodel,bothestimated using60(withaminimum20)daysoflaggedreturns.Weexaminequintilesof
SizeandVar orRVar butincontrasttoothersorts,theNYSEbreakpointsfor
VarandRVararesetseparatelyforeachSizequintile.Thisreflectsthefactthat withunconditionalNYSEbreakpoints,thehighestVar andRVar quintilesare mostlymicrocaps,andthemegacapportfoliosinthehighestvolatilityquintiles arethinandsometimesempty. 2.1.4Accruals. Sloan (1996) is the seminal paper in the literature on the lowreturnsassociatedwithhighaccruals.Accrualsarisebecauseaccounting decisions cause book earnings to differ from cash earnings.

Our tests of the accruals anomaly use 25 VW portfolios formed from the intersection of
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

independentsortsofstocksintoSizeandaccrual(AC)quintiles.Theportfolios areformedattheendofJuneofeachyeart.Sizeismarketcapattheendof
Juneandaccrualsarethechangeinoperatingworkingcapitalpersplit-adjusted sharefromthefiscalyear-endint−2tot−1dividedbybookequitypershare int−1. 2.1.5 Momentum. Jegadeesh and Titman (1993) document momentum in stockreturns.Forexample,therelativeperformanceofstocksinmonthst−12
tot−2tendstopersistinmontht.Weform25VWmomentumportfoliosevery month.The portfolios for month t, formed at the end of month t−1, are the intersectionofquintilesfromindependentsortsonSize(marketcapattheend oft−1),andPrior2–12(thesumofastock’smonthlyreturnsfromt−12to t−2).

The troublesome portfolios in our asset pricing tests are typically in the smallerSizequintiles.Forperspective,withNYSESizebreaks,themicrocap quintileonaveragecontains57%ofNYSE-AMEX-NASDAQstocksbutonly
2.9%ofaggregatemarketcap.ThenextSizequintileonaverageincludes14.7%
ofstocksbutonly3.7%ofaggregatemarketcap.Incontrast,themegacapSize quintileonaverageaccountsfor8.6%ofNYSE-AMEX-NASDAQstocks,but they are 74.8% of aggregate market cap, and the two largest Size quintiles togetheraverage87.3%ofaggregatemarketcap. 2.2 Summarytests
If an asset pricing model captures expected returns, the intercept is indistinguishablefromzerointhetime-seriesregressionofanyasset’sexcess return(itsreturninexcessoftherisk-freerate)onthemodel’sfactorreturns.

Table2showsGibbons,Ross,andShanken’s(1989)GRSstatistic,whichtests thishypothesisforvariantsofregression(3).Thevariantsof(3)weexamine includethethree-factormodelofFF(1993),inwhichtheexplanatoryreturns are R M −R F, SMB, and HML. Also shown are results for three four-factor modelsthatcombineR M −R F andSMBwithpairsofHML,RMW,andCMA, andthefive-factormodel,whichisthefullversionof(3). Weestimateallregressionslopesasconstants,sotimevariationintheslopes isapotentialproblem.Likemostoftheasset-pricingliterature,ourmodelsand testsalsoassumetherearenomarketfrictions,forexample,transactionscosts andtaxes. The GRS results are easily summarized. The test rejects the models we considerand,exceptforoneanomaly,theGRSp-valuesfortherejectionsround to zero to at least three decimal places.

Thus, all the models are incomplete descriptionsofexpectedreturns.Assetpricingmodels,however,aresimplified propositions about expected returns that are rejected in tests with power.We are less interested in whether competing models are rejected than in their relativeperformance,whichwejudgeusingGRSandotherstatistics.Wewant toidentifythemodelthatisthebest(butimperfect)storyforaveragereturns. Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table2
Summarystatisticsfortestsofthree-,four-,andfive-factormodels,July1963–December2014(618
months)
(cid:4) (cid:4)
Modelfactors GRS p(GRS) A|ai| A A (cid:4) | a r ̄i i | (cid:4) A A a r ̄2 i 2 i A A s2 a ( 2 i ai) A(R2)
25Size-βportfolios
Mkt 2.26 0.000 0.232 0.98 0.99 0.18 0.75
MktSMBHML 1.61 0.032 0.106 0.45 0.19 0.38 0.89
MktSMBHMLRMW 1.73 0.016 0.083 0.35 0.13 0.56 0.89
MktSMBHMLCMA 1.51 0.055 0.095 0.40 0.17 0.44 0.89
MktSMBRMWCMA 1.68 0.021 0.069 0.29 0.10 0.81 0.89
MktSMBHMLRMWCMA 1.68 0.021 0.072 0.31 0.10 0.76 0.89
35Size-NIportfolios
MktSMBHML 4.30 0.000 0.136 0.51 0.39 0.18 0.87
MktSMBHMLRMW 3.74 0.000 0.111 0.41 0.24 0.29 0.88
MktSMBHMLCMA 4.03 0.000 0.130 0.49 0.35 0.21 0.87
MktSMBRMWCMA 3.15 0.000 0.100 0.37 0.19 0.39 0.88
MktSMBHMLRMWCMA 3.16 0.000 0.098 0.37 0.18 0.38 0.88
25Size-Varportfolios
MktSMBHML 6.02 0.000 0.217 0.72 0.84 0.06 0.87
MktSMBHMLRMW 5.28 0.000 0.147 0.49 0.49 0.10 0.89
MktSMBHMLCMA 6.08 0.000 0.213 0.71 0.81 0.07 0.87
MktSMBRMWCMA 5.05 0.000 0.130 0.43 0.36 0.14 0.88
MktSMBHMLRMWCMA 5.03 0.000 0.131 0.44 0.36 0.14 0.89
25Size-RVarportfolios
MktSMBHML 7.15 0.000 0.222 0.71 0.80 0.06 0.88
MktSMBHMLRMW 6.33 0.000 0.144 0.46 0.44 0.09 0.90
MktSMBHMLCMA 7.22 0.000 0.222 0.70 0.77 0.06 0.88
MktSMBRMWCMA 5.95 0.000 0.118 0.37 0.32 0.14 0.89
MktSMBHMLRMWCMA 5.94 0.000 0.120 0.38 0.32 0.13 0.90
25Size-ACportfolios
MktSMBHML 3.68 0.000 0.113 0.48 0.26 0.27 0.91
MktSMBHMLRMW 4.57 0.000 0.143 0.61 0.40 0.17 0.91
MktSMBHMLCMA 3.29 0.000 0.096 0.41 0.21 0.34 0.91
MktSMBRMWCMA 3.70 0.000 0.127 0.54 0.32 0.22 0.91
MktSMBHMLRMWCMA 3.77 0.000 0.126 0.54 0.31 0.23 0.91
25Size-Prior2–12portfolios
MktSMBHML 5.06 0.000 0.319 0.97 1.11 0.06 0.85
MktSMBHMLRMW 4.69 0.000 0.305 0.93 0.96 0.07 0.85
MktSMBHMLCMA 4.74 0.000 0.297 0.90 0.97 0.07 0.85
MktSMBRMWCMA 4.25 0.000 0.280 0.85 0.78 0.09 0.84
MktSMBHMLRMWCMA 4.24 0.000 0.272 0.83 0.74 0.09 0.85
MktSMBHMLMOM 3.87 0.000 0.133 0.40 0.17 0.20 0.91
MktSMBHMLRMWMOM 3.72 0.000 0.118 0.36 0.14 0.23 0.92
MktSMBHMLCMAMOM 3.73 0.000 0.135 0.41 0.17 0.20 0.91
MktSMBRMWCMAMOM 3.56 0.000 0.119 0.36 0.15 0.24 0.92
MktSMBHMLRMWCMAMOM 3.55 0.000 0.117 0.36 0.14 0.23 0.92
Thistabletestshowwellthree-,four-,andfive-factormodelsexplainmonthlyexcessreturnsonthe25Size-β
(beta)portfolios,the35Size-NI (netshareissues)portfolios,the25Size-Var(totalvariance)portfolios,the
25Size-RVar(residualvariance)portfolios,the25Size-AC(accruals)portfolios,andthe25Size-Prior2–12
(momentum)portfolios.Thetableshows(1)thefactorsineachregressionmodel,(2)theGRSstatistictesting whethertheexpectedvaluesofall25or35interceptestimatesarezero,(3)p(GRS),thep-valuefortheGRS
statistic,(4)theaverageabsolutevalueoftheintercepts,A|ai|,(5)A|ai|/A|r ̄i|,theaverageabsolutevalueof theinterceptsovertheaverageabsolutevalueofr ̄i,whichistheaverageexcessreturnonportfolioiminus theaverageVWmarketportfolioexcessreturn,(6)Aa
2/Ar ̄
2,theaveragesquaredinterceptovertheaverage squaredvalueofr ̄i,(7)As2(ai)/Aa
2,theaverageoftheestimatesofthevariancesofthesamplingerrorsof theestimatedinterceptsoverAr ̄
2,and(8)AR2,theaveragevalueoftheregressionR2correctedfordegreesof freedom.Eachsortusesallstockswithdataforthetwosortvariablesattheportfolioformationdate.Mktisthe excessreturnontheVWmarketportfolio,RM−RF.TheotherfactorsaredefinedinTable1.

Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

UsingAtoindicateanaveragevalue,theotherstatisticsweusetoevaluate competingmodelsincludetheaverageabsoluteintercept,A|a
|,andtworatios thatmeasurethedispersionoftheintercepts(unexplainedLHSaverageexcess returns)producedbyamodelrelativetothedispersionofLHSaverageexcess returns.Werequirebaselinesorreferencepointstomeasuredispersion.Since theasset-pricinghypothesisisthatthetrueinterceptsarezero,theappropriate referencepointfortheinterceptsiszero.Whatisthebestreferencepointforthe dispersionoftheLHSaverageexcessreturns?Ourcurrentanswerisdifferent fromthatinFF(2015). InFF(2015),thedispersionoftheLHSaverageexcessreturnsismeasured relative to the simple average of all LHS average excess returns.

From an assetpricingperspective,however,theaverageVWmarketexcessreturnisa betterreferencepointforthreereasons:(1)WetakeMerton’s(1973)ICAPM
to be a central motivation for multifactor models.

The VW market portfolio is the centerpiece of the ICAPM: in the language of Fama (1996), the VW
marketportfolioismultifactorefficientinallversionsoftheICAPM.(2)More simply,theVWmarketportfolioisanattractivereferencepointbecauseitis theaggregateoftheportfolioschosenbyinvestors.(3)Anymodelthatincludes
R M −R F asafactorperfectly(andtrivially)explainstheVWmarketportfolio excessreturn.Incontrast,theEWaverageoftheLHSportfolioexcessreturns hasnospecialroleinassetpricing.Forexample,asaLHSportfolio,itsexcess returnalmostsurelyproducesanonzerointerceptinanassetpricingregression, andtheinterceptisdifferentfordifferentassetpricingmodelsanddifferentsets ofLHSportfolios. Definer ̄ i asthedifferencebetweenthetime-seriesaverageexcessreturnon
LHS portfolio i and the average excess return on the VW market.

The first measureoftherelativedispersionoftheinterceptsisA|a
|,theaverage absolute intercept divided by the average absolute value of r ̄ i.The second is
Aa2/Ar ̄2,theaveragesquaredinterceptoverAr ̄2,theaveragesquaredvalue i i i ofr ̄ i. In the end, the denominators of A|a i |/A|r ̄ i | and Aa i 2/Ar ̄ i 2 are just scaling variables:foragivensetofLHSportfolios,thedenominatorsarethesamefor all asset pricing models. They just give perspective on the dispersion of the interceptsinthenumeratorsoftheratios.Switchingthereferencepointfrom theaverageVWmarketreturnusedheretotheEWaverageoftheLHSaverage returnsusedinFF(2015)producesthesameorderingofinterceptdispersion fordifferentmodels.

Finally,inFamaandFrench(2015),weshowresultsforavariantofAa2/Ar ̄2
thatadjustsnumeratoranddenominatorformeasurementerror.Inthosetests, adjusted ratios tend to be a bit smaller than unadjusted ratios. In ongoing testsoninternationaldata,thedoubleadjustmentsometimesproducesextreme ratios, positive and negative. The sample period in the international tests is much shorter, and we suspect the problem is measurement error in estimates
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

ofmeasurementerror,whichisespeciallytroublesomeinthedenominatorof theadjustedratiosinceitcanleadtoexplosiveratiosofeithersign. Wedonotshowdouble-adjustedratioshere.Insteadweshowestimatesofthe proportionofthedispersionoftheinterceptestimatesattributabletosampling error.Thus,theinterceptestimatea i isthetrueintercept,α i,plusanestimation error,ε i, a i=α i+ε i (4)
Sinceα isaconstant,theexpectedvalueofa2is
E(a2)=α2+E(ε2). (5)
i i i
AveragingovertheLHSassets,wehave
AE(a2)=Aα2+AE(ε2). (6)
i i i
Theexpectedvalueofε iiszero,soE(ε
2)isthevarianceofa iduetoestimation error,whichweestimatewiththesquaredsamplestandarderrorofa i,s2(a i). The sample estimate of AE(a
2) is Aa
2.

The ratio As2(a i)/Aa
2 is then our estimateoftheproportionofthedispersion(secondmoment)oftheintercept estimatesduetoestimationerror. Note that low values of A|a i |/A|r ̄ i | and Aa i 2/Ar ̄ i 2 are good news for an assetpricingmodel:theysaythatinterceptdispersion(thedispersionofLHS
averagereturnsleftunexplainedbythemodel)islowrelativetothedispersion oftheLHSaveragereturns.Incontrast,highvaluesofAs2(a i)/Aa
2 aregood news:theysaythatmuchofthedispersionoftheinterceptestimatesisdueto samplingerrorratherthantodispersionofthetrueintercepts. 2.2.1Marketβ.

TheGRSrejectionsofourassetpricingmodelsareweakest fortheSize-β portfolios.Sincetheβ anomalyisapurportedviolationofthe
CAPM,weincludetheCAPMamongthemodelstested.TheCAPMisrejected withaGRSp-valuethatiszerotothreedecimalplaces.TheratiosA|a
|
andAa2/Ar ̄2 are0.98and0.99,sothedispersionofCAPMinterceptsalmost matches the dispersion of average LHS portfolio returns. And As2(a i)/Aa estimates that only about 18% of the dispersion of the intercepts is due to samplingerror.SimilarnegativeresultsareobservedintestsoftheCAPMon portfoliosfromtheotheranomalysorts,andtosavespaceweshownoCAPM
results for other anomalies.

We see later that the CAPM is rejected in the β
sortsbecausethemodelpredictsthattheslopeintherelationbetweenaverage excessreturnandβ istheaverageexcessmarketreturn,buttheactualrelation isessentiallyflat. Inearlierdraftsofthispaper,theFF(1993)three-factormodeleasilypasses the GRS test on the 25 Size-β portfolios (GRS=1.07; p-value = 0.371) and, likeNovy-Marx(2014),weconcludethatreturnsonβ-sortedportfoliosdonot identify problems for the three-factor model.Adding 2014 to the 1963–2013
sample of earlier drafts changes that inference; the three-factor GRS statistic
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

increasesto1.61(Table2)andtheGRSp-valueshrinksto0.032.TheGRStest on the Size-β portfolios also rejects our other models at conventional levels, buttherejectionsareweakerthanforotheranomalies. Adding2014tothe1963–2013samplehaslittleeffectonothermeasuresof performance. Judged on anything but the GRS test, the best performers (in a dead heat) in the tests on the Size-β portfolios are the five-factor model and the four-factor model that drops HML.The average absolute intercepts from thetwomodelsare0.072%and0.069%,versus0.106%fortheFFthree-factor model. The A|a i |/A|r ̄ i | ratios are 0.31 and 0.29 for the five- and four-factor models,someasuredinunitsofreturn,thedispersionofunexplainedaverage returns is about 30% as large as the dispersion of average returns.

In units ofreturnsquared(Aa2/Ar ̄2)thedispersionofunexplainedaveragereturnsis about10%aslargeasthedispersionofaveragereturns.TheratiosAs2(a i)/Aa are0.76and0.81,whichsuggeststhatmorethanthree-quartersofthesecond momentsoftheinterceptestimatesforthetwomodelsisduetosamplingerror andonlyaboutone-fourthisduetodispersioninthetrueintercepts.Allthisis consistentwithrelativelyweakrejectionsontheGRStest. 2.2.2Netshareissues. AlltheassetpricingmetricsinTable2agreethatthe five-factormodelandthefour-factormodelthatdropsHML providethebest descriptionsofaverageSize-NIportfolioreturns.Thus,addingprofitabilityand investmentfactorsenhancesestimatesofexpectedreturnsforportfoliosformed on Size and net issues.

The average absolute intercepts produced by the two models are 0.098% and 0.100% per month.The ratio A|a i |/A|r ̄ i | is 0.37 for bothmodels,soinunitsofreturn,thedispersionoftheestimatedinterceptsis
37%aslargeasthedispersionofaverageSize-NI portfolioreturns.Inunitsof return squared, Aa2/Ar ̄2 is 0.18 and 0.19 for the two models, and the ratios
As2(a i)/Aa
2 estimate that about 40% of Aa
2 is due to sampling error in the intercept estimates. These results suggest that, despite rejection on the GRS
test,thetwomodelsperformwellinthetestsontheSize-NI portfolios.

When we later examine the intercepts produced by the five-factor model
(Section4),weseethatitsproblemsarelargelyinportfoliosofsmallstocksin thehighestNI quintile,whichhavenegativeexposurestoRMW andCMAlike thoseofsmallfirmsthatinvestalotdespitelowprofitability.Thisisthelethal combinationthatplaguesthefive-factormodelinFF(2015). 2.2.3 Volatility.

We also see later (Section V) that the same lethal combination plays a big role in the rejection of the five-factor model in tests ontheSize-Var andSize-RVar (totalandresidualvariance)portfolios.Again, theGRStestandothersummarystatisticsinTable2implythatthefive-factor modelandthefour-factormodelthatdropsHMLprovidethebestdescriptions ofaverageSize-Var andSize-RVar portfolioreturns.Onallmetrics,however, the volatility portfolios pose stronger challenges to the two models than the
Size-NIportfolios.Theaverageabsoluteinterceptsandsevenoftheeightratios
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

comparingthedispersionoftheinterceptstothedispersionoftheLHSaverage returnsarelargerforthevolatilityportfoliosthanforthenetissuesportfolios, andlessofthedispersionoftheinterceptsforthevolatilityportfolioscanbe attributedtosamplingerror. 2.2.4Accruals. InthetestsonthesixdifferentsetsofLHSportfoliosinFF
(2015),andinthetestsonotherLHSportfoliosexaminedhere,thefive-factor modeltypicallyperformsbetterthantheFFthree-factormodel.Thisisnottrue forthe25Size-AC portfolios.TheculpritistheprofitabilityfactorRMW.The threemodelsthatincludeRMW producelargerGRS statisticsandareweaker on other metrics than the two models that do not include RMW.

In contrast, modelsthatincludetheinvestmentfactorCMAperformrelativelywell,except whentheyincludeRMW.FortheSize-ACportfolios,thefour-factormodelthat dropsRMW deliversthebestperformanceonallmetrics.Theperformanceof thismodelinthetestsforaccrualsissimilartothatofthebestmodelsinthe testsfornetissuesandvolatility.Weseelaterthatthepoorperformanceofthe five-factormodelintheaccrualstestsowesalottomicrocaps. 2.2.5 Momentum. Models that do not include MOM fail badly as descriptionsofaveragereturnsonthe25Size-Prior2–12portfolios.Forexample,the estimates of intercept dispersion relative to the dispersion of average excess returns,A|a
|,rangefrom0.97fortheFFthree-factormodelto0.83for thefive-factormodel.Allarefarabovethevaluesofthisratiointhesortsfor otheranomalyvariables.

Whenweincludethemomentumfactor,MOM,allmodelsarestillrejected ontheGRStest,butexplanatorypowerimproves.ThebestmodelsontheGRS
testarethesix-factormodelthataddsMOM tothefive-factormodelandthe five-factor model that drops HML. The performance of these two models is essentially identical on all metrics.The average absolute intercept is 0.117%
per month with HML and 0.119% without. In units of return, the dispersion oftheinterceptsrelativetothedispersionofSize-Prior2–12averagereturns,
A|a
|,is0.36forbothmodels,andinunitsofreturnsquared,Aa
2/Ar ̄
2, itis0.14foroneand0.15fortheother.Thesearestrongnumbers,buttheyare achievedbyaddingamomentumfactorconstructedwithacoarserversionofthe sortsforthe25Size-Prior2–12portfolios,aluxurynotallowedinthetestsfor other anomalies.

Moreover, when MOM is among the factors, other models, including Carhart’s (1997) model, which adds MOM to the FF three-factor model,performalmostaswellasthesix-factormodel. 2.3 Thefive-factormodelversustheFFthree-factormodel:Asimpletest
For almost all sorts examined here and in FF (2015), the five-factor model performsbetterthantheFFthree-factormodel.Arethedifferencesstatistically reliable?Ifweassumeexpectedreturnsaregovernedbyalinearfactormodel andsomestockshavenonzeroexposurestoRMW andCMA,wecanusethe
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

GRS test to show formally that the profitability and investment factors add informationaboutexpectedreturnstothethree-factormodel. TheGRS testontheinterceptsfromFFthree-factorregressionstoexplain
RMW andCMAtellsuswhetheraddingRMW andCMAimprovesthemeanvarianceefficientsetproducedbycombiningtherisk-freerate,R M −R F,SMB, andHML.Theregressionestimates(t-statisticsinparentheses)are
RMWt=0.33 − 0.05(R
−R Ft)−0.23SMBt+0.01HMLt+e t
,
(4.08)(−2.64) (−8.43) (0.33) R2=0.14 (7)
CMAt=0.20 − 0.09(R
−R Ft)+0.01SMBt+0.45HMLt+e t
.

(3.62)(−6.70) (0.52) (22.12) R2=0.53 (8)
Theinterceptsintheseregressions—0.33(t=4.08)forRMW and0.20(t=
3.62) for CMA—are large, even by the standards suggested by Harvey, Liu, andZhu(2015).TheGRSstatistic(21.09;p-valuezerotoatleastfivedecimal places) confirms that RMW and CMA jointly add to the information about expectedreturnsinR M −R F,SMB,andHML.

Factorredundancytestslikeregressions(7)and(8)aredefinitive.Ifafactor’s averagereturniscapturedbyitsexposurestotheotherfactorsinamodel,that factoraddsnothingtothemodel’sexplanationofaveragereturns,andnosetof
LHSportfolioscanoverturnthisconclusion(Fama1998;BarillasandShanken
2015).Conversely,ifafactor’saveragereturnisnotcapturedbyitsexposures to the other factors in a model, that factor has a role in explaining average returnsinthemodel.Thisdoesnotmeanthisfactorisimportantforexplaining average returns for all sets of LHS portfolios. For example, exposures to an importantfactormaybenegligibleinaparticularLHSsort,inwhichcasethat factormaynothelpexplainaveragereturnsinthatsort.

2.4 Anequivalentfive-factormodel
InthesummarytestsofTable2,thefive-factormodelandthefour-factormodel thatdropsHMLperformalmostidenticallyonallmetrics.Thisresultisinline with the evidence in FF (2015) that HML is redundant for describing U.S. average returns, at least for 1963–2014. Specifically, the large average HML
return (0.36% per month; t=3.15 in Table 1) is absorbed by the exposures of HML to other factors, especially the profitability and investment factors,
RMW andCMA.Forthetimeperiodandversionofthefactorsusedhere,the regressiontoexplainHML(t-statisticsinparentheses)is
HMLt= −0.04 + 0.01(R Mt −R Ft)+0.03SMBt+0.22RMWt+1.04CMAt+e t . (−0.47) (0.31) (0.88) (5.37) (23.24) R2=0.51
(9)
In contrast, R M −R F, SMB, RMW, and CMA have substantial marginal information about average returns.

Skipping the details, the intercepts in the
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

regressionstoexplaineachofthesefactorreturnswiththeotherfourare0.81
(t=5.00)forR
M
−R F,0.36(t=3.09)forSMB,0.42(t=5.33)forRMW,and
0.27(t=4.98)forCMA. The trivial intercept in (9) implies that nothing is lost in the explanation ofaveragereturnsifwedropHML fromthefive-factormodel.Exposuresto
HMLare,however,importantforunderstandingtheportfoliotypesthatcause asset-pricingproblems.WewanttokeepHML,butwealsowantotherfactors to have slopes that reflect the fact that, at least in U.S. data for 1963–2014, the four-factor model that drops HML captures average stock returns as well as the five-factor model.Atwist on the five-factor model meets these goals. DefineHMLO(orthogonalHML)asthesumoftheinterceptandresidualfrom
(9).

Substituting HMLO for HML in (3) produces an alternative five-factor regression:
R
−R Ft=a i+b i(R
−R Ft)+s iSMBt+h iHMLOt+r iRMWt+c iCMAt+e
.

(10)
Theinterceptandresidualin(10)arethesameasinthefive-factorregression
(3),sothetworegressionsareequivalentforjudgingmodelperformance.For example,theGRStestandotherresultsforthefive-factormodelinTable2do notchangeifweuse(10)ratherthan(3).TheHMLOslopein(10)isalsothe sameastheHMLslopein(3),so(10)producesthesameestimateofthevalue tiltoftheLHSportfolio.ButtheestimatedmeanofHMLO(theinterceptinthe
HMLregression(9))isnearzero(−0.04;t=−0.47),soitsslopeaddslittleto theestimateoftheexpectedLHSreturnfrom(10).Theslopesonotherfactors in(10)arethesameasinthefour-factormodelthatdropsHML,sootherfactors haveslopesthatreflectthefactthattheycapturetheinformationinHMLabout averagereturns.

Formoreinsightintomodelperformance,wenextexaminetheassetpricing regressionsfortheanomalyportfoliosinmoredetail.Foreachanomaly,wefirst documentthepatternsinaveragereturnsweseektoexplain.Wethenexamine interceptsandpertinentslopesfromassetpricingregressions. 3. Marketβ
PanelAof Table 3 shows average monthly excess returns (returns in excess oftheone-monthU.S.Treasury-billrate)onthe25VWSize-β portfolios.The resultsconfirmpreviousevidencethatthereisnoclearrelationbetweenβ and average return.

For example, the portfolio in the highest β quintile of a Size quintiletendstohaveaslightlyhigheraveragereturnthantheportfoliointhe lowestβ quintile.Buttheportfoliointhehighestβ quintilealsohasalower averagereturnthanportfoliosinthemiddlethreeβquintilesofaSizequintile, which have similar average returns.There is, however, a size effect in every
β quintile: given β, average return is highest for microcaps and lowest for megacaps. Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table3
Averageexcessreturnsandcharacteristicsofstocksinthe25Size-βportfolios,July1963–December2014
(618months)
Low β 2 3 4 Highβ Lowβ 2 3 4 Highβ
PanelA:AverageexcessreturnsandSD
Small 0.73 0.90 0.92 0.98 0.79 4.41 5.10 5.95 6.51 8.23
2 0.72 0.86 0.95 0.89 0.72 4.30 4.77 5.48 6.21 7.92
3 0.69 0.86 0.84 0.80 0.76 3.85 4.65 5.22 5.96 7.69
4 0.67 0.76 0.74 0.58 0.75 3.89 4.63 5.17 5.84 7.57
Big 0.49 0.52 0.49 0.50 0.41 3.63 4.25 4.88 5.69 7.15
PanelB:AverageB/M, OP,Inv,andpriorβcharacteristics
Small 0.99 1.04 1.04 1.04 0.94 0.15 0.14 0.16 0.37 0.02
2 0.88 0.87 0.84 0.82 0.76 0.26 0.25 0.47 0.27 0.23
3 0.85 0.79 0.75 0.72 0.68 0.26 0.30 0.31 0.31 0.25
4 0.80 0.72 0.69 0.69 0.66 0.29 0.31 0.30 0.29 0.31
Big 0.65 0.51 0.57 0.56 0.63 0.35 0.40 0.34 0.37 0.36
Inv Priorβ
Small 0.10 0.09 0.10 0.11 0.14 0.31 0.84 1.15 1.51 2.49
2 0.12 0.12 0.13 0.15 0.20 0.38 0.84 1.16 1.51 2.40
3 0.12 0.12 0.13 0.15 0.23 0.38 0.84 1.15 1.50 2.32
4 0.10 0.12 0.13 0.14 0.21 0.40 0.84 1.15 1.50 2.24
Big 0.10 0.12 0.14 0.15 0.21 0.42 0.83 1.15 1.48 2.10
AttheendofJunefrom1963to2014,weformvalue-weightportfoliosusingindependentsortsofNYSE,AMEX, and(beginningin1973)NASDAQstocksintoSize(marketcapitalization)quintilesandquintilesofβ(market beta),withNYSEbreakpointsforbothvariables.Theintersectionsofthetwosortsproduce25Size-βportfolios.

ForportfoliosformedinJuneofyeart,SizeismarketcapitalizationattheendofJuneandβismarketbeta estimatedbyregressingastock’smonthlyreturnonthecurrentmarketreturn,estimatedusingthe60(witha minimum24)monthsofreturnsprecedingJuneoft.PanelAshowsmeansandstandarddeviationsofmonthly excessreturnsonthe25portfolios.PanelBshowstime-seriesmeansoftheportfoliobook-to-marketequity ratio(B/M),operatingprofitability(OP),andinvestment(Inv)forthefiscalyearendinginthecalendaryear precedingportfolioformation.ForportfoliosformedattheendofJuneofyeart,B/M,OP,andInvinpanelB
arevalue-weightaverages(market-capweights)ofthevariablesforthefirmsinaportfolio.Specifically,B/M
isthevalue-weightaverageratioofbookequityatthefiscalyear-endincalendaryeart−1andmarketcapat theendofDecemberoft−1;OPisthevalue-weightaverageratioofoperatingprofitsandbookequityforthe fiscalyearendingint−1;andInvisthevalue-weightaveragerateofgrowthoftotalassetsforthefiscalyear endingint−1.PanelBalsoshowstheβestimatesusedtoformportfoliosinJuneofeachyeart,firstaveraged acrossthestocksinaportfolioandthenaveragedacrossyears.

Table 4 shows intercepts and slopes for the 25 Size-β portfolios produced by the CAPM and the five-factor model (10).The CAPM regressions (panel
A)showthatsortsonpriorβ estimatesproducelargespreadsinβ estimated using post-sort returns. Since average returns do not increase systematically withβ,itisnotsurprisingthattheCAPMinterceptsarestronglypositivefor low β portfolios. Megacaps aside, most of the CAPM intercepts in the four lowerquintilesofβarereliablypositiveandthoseinthehighestβquintileare nearzero.Megacapsproducethesmallestinterceptineachβ quintile,andthe onlyreliablynegativeCAPMintercept,−0.31%(t=−2.29),isformegacaps inthehighestβ quintile.

The five-factor model cures the systematic problems of the CAPM in the testsonthe25Size-β portfolios.ThestrongpositiveCAPMinterceptsinthe fourlowerSizeandβ quintilesdisappearinthefive-factorresults(panelBof
Table4).ThenegativeCAPMinterceptforthemegacapportfoliointhehighest
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table4
Regressionsforthe25Size-βportfolios,July1963–December2014(618months)
Low β 2 3 4 Highβ Lowβ 2 3 4 Highβ
PanelA:CAPM:Rit–RFt=ai+bi(RMt–RFt)+eit
Small 0.34 0.44 0.39 0.36 0.04 2.96 3.45 2.60 2.45 0.22
2 0.33 0.40 0.41 0.28 −0.07 3.11 3.82 3.68 2.23 −0.42
3 0.32 0.39 0.31 0.19 −0.02 3.70 4.66 3.33 1.80 −0.13
4 0.30 0.28 0.19 −0.04 −0.03 3.39 3.74 2.50 −0.41 −0.19
Big 0.15 0.07 −0.03 −0.11 −0.31 1.77 1.03 −0.50 −1.42 −2.29
Small 0.75 0.90 1.04 1.21 1.48 29.13 31.51 31.18 36.27 33.20
2 0.77 0.90 1.07 1.21 1.55 32.61 38.58 43.25 43.53 44.32
3 0.71 0.93 1.05 1.20 1.54 36.51 49.90 50.34 50.08 49.26
4 0.72 0.95 1.08 1.22 1.53 36.46 57.55 63.68 61.60 51.71
Big 0.67 0.89 1.04 1.20 1.42 35.21 61.82 72.92 68.40 46.97
PanelB:Five-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLOt+riRMWt+ciCMAt+eit
Small 0.07 0.06 0.04 0.08 −0.03 1.07 0.98 0.63 1.27 −0.31
2 0.04 0.02 0.05 −0.06 −0.15 0.57 0.31 0.90 −0.99 −2.03
3 0.09 0.10 0.00 −0.11 −0.02 1.16 1.70 0.07 −1.55 −0.25
4 0.07 −0.02 −0.09 −0.24 0.08 0.84 −0.24 −1.37 −2.98 0.72
Big −0.07 −0.07 −0.09 −0.09 −0.06 −1.08 −1.38 −1.52 −1.14 −0.45
Small 0.66 0.81 0.89 1.02 1.14 40.86 51.46 56.20 69.41 56.64
2 0.73 0.86 0.99 1.10 1.29 40.23 63.70 69.69 75.42 70.14
3 0.75 0.92 1.01 1.13 1.31 40.85 63.62 66.61 65.78 59.72
4 0.81 1.01 1.10 1.19 1.35 40.68 65.09 69.59 62.12 50.15
Big 0.83 0.98 1.08 1.18 1.30 50.97 75.20 74.85 59.75 39.24
s t(s)
Small 0.77 0.93 1.12 1.14 1.40 34.05 42.18 50.18 54.95 49.30
2 0.60 0.74 0.81 0.95 1.11 23.81 39.13 40.50 46.68 42.85
3 0.27 0.50 0.61 0.72 0.87 10.56 24.94 28.51 29.87 28.29
4 0.04 0.24 0.32 0.38 0.56 1.31 10.88 14.37 14.13 14.88
Big −0.28 −0.17 −0.11 0.06 0.06 −12.27 −9.32 −5.35 2.06 1.25
Small 0.30 0.26 0.22 0.22 −0.09 9.35 8.32 7.18 7.72 −2.38
2 0.33 0.30 0.24 0.17 −0.06 9.37 11.42 8.76 5.99 −1.67
3 0.38 0.19 0.21 0.21 −0.12 10.71 6.80 6.90 6.30 −2.71
4 0.33 0.21 0.13 0.20 −0.09 8.38 6.76 4.15 5.38 −1.63
Big 0.10 0.04 0.06 0.09 −0.10 3.03 1.71 2.07 2.41 −1.57
Small 0.05 0.18 0.03 0.01 −0.47 1.49 5.73 0.83 0.44 −11.67
2 0.13 0.32 0.30 0.21 −0.22 3.59 11.71 10.33 7.12 −5.80
3 0.13 0.25 0.29 0.28 −0.17 3.60 8.51 9.57 8.21 −3.95
4 0.17 0.33 0.35 0.23 −0.33 4.26 10.59 10.89 6.05 −6.21
Big 0.31 0.31 0.26 0.11 −0.26 9.41 11.81 8.98 2.77 −3.96
Small 0.33 0.42 0.38 0.23 −0.08 9.32 12.39 11.05 7.28 −1.90
2 0.38 0.42 0.33 0.29 −0.10 9.60 14.25 10.65 9.12 −2.52
3 0.40 0.33 0.30 0.25 −0.24 10.20 10.66 9.08 6.66 −4.98
4 0.45 0.39 0.30 0.17 −0.26 10.52 11.70 8.84 4.16 −4.40
Big 0.44 0.19 0.01 −0.14 −0.44 12.60 6.77 0.17 −3.33 −6.16
TheLHSvariablesineachsetof25regressionsarethemonthlyexcessreturnsonthe25Size-βportfolios.The
RHSvariablesaretheexcessmarketreturn,RM−RF,theSizefactor,SMB,theorthogonalvaluefactor,HMLO, theprofitabilityfactor,RMW,andtheinvestmentfactor,CMA.ThetableshowsCAPM(panelA)andfive-factor
(panelB)interceptsandregressionsslopes.

Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

βquintilealsobecomesinconsequential(−0.06;t=−0.45).Theonlyblemish onthefive-factormodelistheinterceptfortheintersectionofthefourthSize andfourthβ quintiles,−0.24(t=−2.98). The improvements in the description of average returns on the Size-β
portfoliosprovidedbythefive-factormodeltracetopatternsinthefive-factor regressionslopesthatabsorbthepatternsinaveragereturns.PanelBofTable4
shows that portfolios in the four lower β quintiles tilt toward value (positive
HMLO slopes) and portfolios in the highest β quintile have a growth tilt
(negativeHMLOslopes),butsincetheaverageHMLOreturnisclosetozero thesetiltshavelittleimpactonfive-factorintercepts.Theheavyliftingisdone by the RMW and CMA slopes.

Microcaps aside, the five-factor RMW slopes are strongly positive in the four lower β quintiles.The RMW slopes become stronglynegativeinthehighestβquintile,especiallyformicrocaps.InallSize quintilestheCMAslopesarepositiveinthelowerβquintilesbutturnstrongly negativeinthehighestβ quintile.Inshort,thereturnsonlowβ stocksbehave likethoseofprofitablefirmsthatinvestconservatively,whereasthereturnson highβ stockstrackthoseoflessprofitablefirmsthatinvestalot. TheRMW andCMAslopesofthefive-factormodelincreasethepredicted returns on the low β portfolios of the Size-β sorts and reduce the predicted returnsonthehighβportfolios.Butthelowandhighβportfolioshavesimilar averagereturns,sofive-factorinterceptsclosetozeroimplythattheslopesfor the market and/or SMB lean against the RMW and CMA slopes.

Panel B of
Table4showsthatthespreadsinthefive-factormarketslopesforthelowest andhighestβportfoliosofgivenSizequintilesarelarge,from0.47to0.56.The averagemarketpremiumfor1963–2014is0.51%permonth,sothespreadsin averagereturnspredictedbythespreadsinR –R slopesarealsolarge,0.24%
M F
to0.29%permonth.Surprisingly,ineverySizequintileSMBslopesincrease monotonicallyfromlowβ tohighβ quintiles,andthespreadsareagainlarge, from 0.34 for megacaps to 0.63 for microcaps. The average SMB return for
1963–2014 is 0.27% per month, so the spreads in average returns predicted bythespreadsintheSMBslopesrangefrom0.09%(megacaps)to0.17%per month (microcaps).

In short, the five-factor market and SMB slopes, and the associatedpremiums,offsetRMW andCMAslopesandpremiumstocapture averagereturnsthatshowlittletendencytoincreasewithCAPMβ. The results suggest that average returns vary with multivariate β (market slopeb)inthewaypredictedbythefive-factormodel,eventhoughthereislittle relationbetweenCAPMβandaveragereturns.Forperspective,weestimatea four-factormodelthatdropsthemarketfactorfromthefive-factormodel(3)
andusesreturnsonthe25Size-β portfoliosmeasuredinexcessofthemarket return as LHS variables. In other words, we set all multivariate βs equal to
1.0.

Skipping the details, the intercepts from this model are negative for the five portfolios in the lowest β quintile, and three of five are more than two standarderrorsbelowzero.Theinterceptsforthefiveportfoliosinthehighest
β quintile are positive, and three of five are more than two standard errors
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

above zero. Thus, setting multivariate βs equal to 1.0 produces forecasts of averagereturnsthataretoohighforlowβ portfoliosandtoolowforhighβ
portfolios.We conclude that there is a positive relation between multivariate
β andaveragereturns,andtheaveragepremiumformultivariateβ conforms welltothefive-factormodel. Sincelotsofwhatiscommoninthestoryforaveragereturnsfordifferent setsofLHSanomalyportfolioscentersontheslopesforRMW andCMA,an interesting question is whether the slopes line up with profitability (OP) and investment(Inv)characteristics.LiketheCMAslopesoftheSize-β portfolios, averageinvestmentincreasesfromlowertohigherβ quintiles(Table3).But contradicting the RMW slopes, profitability (OP) is not systematically lower for high β portfolios, except perhaps for microcaps.

This is not surprising. Multivariate regression slopes estimate marginal effects, holding constant other explanatory variables, so the slopes need not line up with univariate characteristics. Since characteristics do not always line up with regression slopes, we are carefulwhendescribingtheslopes.Forexample,wesaythatstrongnegative
RMW and CMA slopes for the portfolios in the highest β quintile imply that returns on these stocks “behave like” those of unprofitable firms that invest aggressively. Table 3 shows these firms have grown rapidly, but except for microcaps,theyhavenotbeenalotlessprofitablethanlowerβ portfoliosof thesameSizequintile. 4.

NetShareIssues
PanelAofTable5showsaverageexcessreturnsforthe35VWportfoliosfrom independentsortsofstocksintoSizequintilesandsevennetshareissues(NI)
groups.Repurchases(negativeNI)areassociatedwithhigheraveragereturns. InallSizegroupsaveragereturnsaresimilarforthelowestthreequintilesof positive NI, but average returns are lower in the fourth quintile.The striking result,andtheresultthatwillbedifficulttoexplainfully,istheextremelow average returns of the five portfolios in the highest NI quintile (largest net issues).Thoughnotourmaininterest,thereisaSizeeffectineveryNI group: microcapshavehigheraveragereturnsthanmegacaps. The summary tests in Table 2 say that the five-factor model improves the description of average returns on the Size-NI portfolios provided by the FF
three-factor model.

Table 6 shows the three-factor and five-factor intercepts andthefive-factorHMLO,RMW,andCMAslopes.WedonotshowR
M
−R
F
andSMBslopessincetheyaresimilarfordifferentmodelsandsocannotexplain theinterceptimprovementsproducedbythefive-factormodel. Inpreviousresearch,repurchasesareassociatedwithpositiveunexplained average returns. The three-factor intercepts for the repurchase portfolios are positive, 0.11% to 0.24% per month, and 1.96 to 3.62 standard errors from zero.Theinterceptsaresmallerinthefive-factormodel,andthelargest,0.10%
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table5
Averageexcessreturnsandcharacteristicsofstocksinthe35Size-NIportfolios,July1963–December
2014(618months)
NI→ Neg Zero Low 2 3 4 High Neg Zero Low 2 3 4 High
PanelA:AverageexcessreturnsandSD
Small 1.05 0.78 0.89 0.94 1.02 0.71 0.24 5.67 5.72 6.36 6.42 6.85 7.12 7.73
2 0.92 0.82 0.92 0.90 0.87 0.80 0.32 5.31 5.66 5.84 6.13 6.31 6.52 7.09
3 0.97 0.76 0.84 0.93 0.82 0.72 0.29 5.09 5.46 5.26 5.64 5.84 6.00 6.53
4 0.94 0.57 0.65 0.70 0.81 0.61 0.35 4.91 4.90 5.07 5.32 5.45 5.79 6.17
Big 0.62 0.61 0.49 0.47 0.59 0.43 0.18 4.18 4.78 4.25 4.54 4.85 5.41 5.12
PanelB:AverageB/M,OP,Inv,andNIcharacteristics
Small 1.05 1.17 1.03 0.93 0.86 0.75 0.68 0.31 0.21 0.18 0.22 0.23 0.06 −0.10
2 0.86 1.00 0.86 0.79 0.73 0.67 0.63 0.27 0.31 0.28 0.30 0.54 0.23 0.18
3 0.78 0.92 0.84 0.73 0.68 0.65 0.64 0.31 0.30 0.27 0.26 0.30 0.23 0.26
4 0.69 0.90 0.79 0.68 0.67 0.65 0.68 0.34 0.27 0.28 0.28 0.32 0.31 0.24
Big 0.59 0.81 0.59 0.52 0.53 0.61 0.71 0.37 0.32 0.36 0.35 0.46 0.32 0.30
Inv NI
Small 0.06 0.06 0.07 0.08 0.10 0.14 0.59 −4.99 0.00 0.14 0.52 1.28 3.85 36.60
2 0.08 0.11 0.10 0.11 0.13 0.18 0.58 −4.58 0.00 0.14 0.52 1.28 3.89 34.34
3 0.08 0.11 0.09 0.11 0.14 0.19 0.53 −3.85 0.00 0.14 0.52 1.29 3.94 28.96
4 0.07 0.07 0.09 0.11 0.13 0.18 0.45 −3.34 0.00 0.14 0.52 1.28 3.96 24.82
Big 0.08 0.10 0.09 0.12 0.13 0.18 0.41 −2.00 0.00 0.13 0.51 1.28 3.84 22.65
AttheendofJuneeachyearfrom1963to2014,weformvalue-weight(VW)portfoliosusingindependentsorts ofNYSE,AMEX,and(beginningin1973)NASDAQstocksintoSize(marketcapitalization)quintilesandinto sevenNI(netshareissues)groups,includingstockswithnegativeNI(repurchases),zeroNI,andquintilesof positiveNI(netissues),usingNYSEbreakpointsforbothvariables.Theintersectionsofthetwosortsproduce
35Size-NIportfolios.ForportfoliosformedinJuneofyeart,SizeismarketcapitalizationattheendofJuneand
NIisthechangeinthenaturallogofsplit-adjustedsharesoutstandingfromthefiscalyear-endint−2tothefiscal year-endint−1.PanelAshowsmeansandstandarddeviationsofmonthlyexcessreturnsonthe35portfolios.

PanelBshowstime-seriesmeansoftheportfoliobook-to-marketequityratio(B/M),operatingprofitability
(OP),andinvestment(Inv)forthefiscalyearendinginthecalendaryearprecedingportfolioformation,as definedinTable3.PanelBalsoshowsthetime-seriesaveragevaluesofNIusedtoformportfolioseachyear. permonth,isonly1.73standarderrorsfromzero.Theinterceptimprovements producedbythefive-factormodelcenterontheRMW andCMAslopes.The repurchase portfolios have strong positive exposures to CMA, RMW, and, megacapsaside,HMLO.Inotherwords,theirreturnscovarypositivelywiththe returnsofvaluestocksandstocksofprofitable,lowinvestmentfirms.Positive exposurestoRMW andCMAincreasefive-factorestimatesofexpectedreturns andleadtonegligibleintercepts.Inshort,therepurchaseanomalydisappears inthefive-factormodel.

Therearenoseriousproblemsinthethree-factorandfive-factorintercepts forportfolioswithzeroNIandinthetwolowestquintilesofpositiveNI.Three portfoliosinthethirdquintileofNIhavethree-factorandfive-factorintercepts nearormorethan2.0standarderrorsabovezero.Theseunexplainedaverage returnsarepositive,butthenetissuesanomalyisaboutthelowaveragestock returnsoffirmsthatissuestock.Chanceisapossibleexplanation. Thenetissuesanomalyisstronginthethree-factorregressionsforportfolios in the highest NI quintile, with negative intercepts from −0.28% per month
(t=−3.03)fortheportfoliointhefourthSizequintileto−0.57%(t=−6.20)
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table6
Regressionsforthe35Size-NIportfolios,July1963toDecember2014(618months)
NI→ Neg Zero Low 2 3 4 High Neg Zero Low 2 3 4 High
PanelA:Three-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLt+eit
Small 0.21 −0.02 −0.00 0.06 0.18 −0.14 −0.57 3.47 −0.29 −0.02 0.88 2.52 −1.84 −6.20
2 0.11 0.04 0.09 0.07 0.07 0.04 −0.43 1.96 0.36 1.24 1.00 1.04 0.57 −5.70
3 0.24 0.03 0.05 0.17 0.12 0.01 −0.37 3.62 0.23 0.72 2.46 1.63 0.15 −4.57
4 0.23 −0.01 −0.06 0.02 0.20 0.01 −0.28 3.41 −0.04 −0.86 0.33 2.77 0.14 −3.03
Big 0.15 0.15 0.07 0.05 0.14 0.01 −0.36 2.71 1.09 0.99 0.78 1.98 0.17 −4.24
PanelB:Five-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLOt+riRMWt+ciCMAt+eit
Small 0.10 −0.05 −0.03 0.02 0.22 −0.04 −0.36 1.73 −0.66 −0.44 0.33 3.11 −0.53 −4.36
2 −0.03 −0.06 0.01 −0.01 0.05 0.12 −0.24 −0.64 −0.53 0.09 −0.19 0.69 1.79 −3.34
3 0.08 −0.01 −0.02 0.12 0.11 0.09 −0.11 1.29 −0.10 −0.29 1.69 1.43 1.25 −1.56
4 0.06 −0.18 −0.19 −0.07 0.23 0.14 0.01 1.00 −1.41 −2.52 −0.90 3.12 1.71 0.13
Big 0.01 0.00 −0.07 0.03 0.16 0.20 −0.18 0.15 0.02 −0.99 0.49 2.22 2.40 −2.23
Small 0.26 0.23 0.21 0.12 −0.06 −0.03 −0.22 9.18 5.70 5.85 3.55 −1.83 −0.93 −5.45
2 0.25 0.35 0.25 0.07 0.02 −0.03 −0.12 9.88 6.43 7.65 2.16 0.77 −1.01 −3.46
3 0.22 0.30 0.38 0.14 −0.00 0.06 −0.03 7.49 5.07 10.87 4.09 −0.11 1.57 −0.97
4 0.22 0.07 0.23 0.12 −0.03 −0.11 0.06 7.16 1.17 6.48 3.27 −0.78 −3.03 1.55
Big 0.00 0.12 0.00 −0.03 −0.03 −0.12 0.32 0.09 1.75 0.07 −0.85 −0.76 −3.03 8.14
Small 0.27 0.09 0.07 0.04 −0.22 −0.25 −0.61 9.23 2.31 1.89 1.14 −6.18 −6.91 −15.04
2 0.37 0.38 0.29 0.14 0.06 −0.17 −0.41 14.15 6.87 8.37 4.12 1.72 −5.33 −11.76
3 0.44 0.10 0.29 0.14 0.03 −0.10 −0.45 14.89 1.67 8.24 3.95 0.88 −2.66 −12.57
4 0.39 0.26 0.28 0.21 −0.07 −0.35 −0.57 12.51 4.17 7.77 5.70 −1.93 −9.07 −13.90
Big 0.22 0.21 0.29 0.09 0.01 −0.40 −0.13 8.60 3.11 8.81 2.83 0.28 −9.76 −3.25
Small 0.44 0.32 0.33 0.29 0.06 −0.11 −0.32 14.03 7.21 8.43 7.74 1.63 −2.84 −7.29
2 0.46 0.36 0.29 0.28 0.05 −0.16 −0.44 16.56 5.96 7.77 7.31 1.27 −4.62 −11.68
3 0.37 0.45 0.41 0.22 −0.01 −0.17 −0.56 11.63 6.91 10.64 5.74 −0.13 −4.21 −14.57
4 0.49 0.54 0.47 0.28 −0.08 −0.20 −0.43 14.33 7.88 11.90 6.91 −2.14 −4.68 −9.79
Big 0.33 0.54 0.19 −0.10 −0.16 −0.43 −0.20 12.12 7.22 5.40 −2.82 −4.17 −9.76 −4.62
TheLHSvariablesarethemonthlyexcessreturnsonthe35Size-NI(netshareissues)portfolios.TheRHSvariablesaretheexcessmarketreturn,RM−RF,theSizefactor,SMB,thevalue factor,HML,oritsorthogonalcounterpart,HMLO,theprofitabilityfactor,RMW,andtheinvestmentfactor,CMA.PanelAshowstheregressioninterceptsfromtheFFthree-factormodel andpanelBshowsregressioninterceptsandHMLO,RMW,andCMAslopesfromthefive-factormodel(10).

Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

formicrocaps.Thefive-factorinterceptsfortheseportfoliosarelessextreme due to negative RMW and CMA slopes that lower five-factor estimates of expectedreturns.Butthenetissuesanomalysurvivesinthefive-factormodel: theinterceptsforfourofthefiveportfoliosinthehighestNIquintilearenegative andthreearemorethan2.2standarderrorsbelowzero. Theunexplainedaveragereturnsassociatedwithlargenetissueshavelotsin commonwiththefive-factorassetpricingproblemsinthesortsonSize,B/M,
OP,andInvinFF(2015).TheportfoliosinthehighestNIquintilehavenegative
RMW andCMAslopes,sotheirreturnsbehavelikethoseofthestocksoffirms withlowprofitabilityandhighinvestment.Smallstockswiththiscombination ofRMW andCMAexposuresarethemajorproblemforthefive-factormodel in many LHS sorts in FF (2015).

But the highest NI megacap portfolio also hasanegativefive-factorintercept,−0.18%(t=−2.23),andhighinvestment despitelowprofitabilityisnotaproblemamonglargestocksinFF(2015). TheRMW andCMAslopesfortheSize-NIportfoliosinTable6lineupwith theiraverageprofitabilityandinvestmentcharacteristics,OPandInv,inTable5. Firmsthatrepurchaseareonaveragemoreprofitablethanfirmsthatmakelarge share issues (Table 5), but the decline in RMW slopes from repurchasers to extremeissuersissharper(Table6).Thereisstrongercorrespondencebetween
CMAslopesandInv.Firmsthatrepurchaseonaveragehavethelowestratesof investment,whichisinlinewithstrongpositiveCMAslopes,andlargeshare issuessignalhighratesofinvestmentmatchedbystrongnegativeCMAslopes.

The jumps in NI and Inv from the fourth to the fifth quintile of NI are impressive.Netissuesaveragelessthan4%ofstockoutstandinginthefourth
NI quintile, rising to 22.65% (megacaps) to 36.60% (microcaps) in the fifth quintile. Investment is 14% to 19% of assets in the fourth NI quintile, rising to 41% (megacaps) to 59% (microcaps) in the fifth. The extreme rates of investment and net issues in the fifth NI quintile suggest that lots of these firms do mergers financed with stock, a combination known to be associated with low stock returns (Loughran and Vijh 1997). The overlap among new issues,mergersfinancedwithstock,andthecombinationoflowprofitability andhighinvestmentthatisafive-factorasset-pricingproblemhereandinFF
(2015)isaninterestingtopicforfutureresearch. 5.

Volatility
Table7showssummarystatisticsforthe25VWSize-RVar(residualvariance)
portfolios. Table 8 shows intercepts and slopes for the portfolios from the five-factorregression(10),alongwiththeinterceptsfromtheFFthree-factor model.Thecorrespondingresultsforthe25Size-Var(totalvariance)portfolios aresimilarandareinTablesA1andA2oftheAppendix. FormegacapsthereisnorelationbetweenaveragereturnandRVar(Table7). For microcaps, the portfolios in the two highest RVar quintiles have lower average returns and the average excess return of the portfolio in the highest
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table7
Averageexcessreturnsandcharacteristicsofstocksinthe25Size-RVarportfolios,July1963–December
2014(618months)
RVar→ Low 2 3 4 High Low 2 3 4 High
Small 1.01 1.17 1.08 0.81 −0.20 4.18 5.64 6.48 7.52 8.99
2 0.92 1.03 1.07 0.97 0.18 4.12 5.30 5.96 6.82 8.45
3 0.75 0.91 0.93 0.93 0.36 3.79 4.86 5.42 6.20 7.79
4 0.72 0.75 0.75 0.78 0.44 3.84 4.53 5.17 5.72 7.41
Big 0.47 0.52 0.51 0.48 0.45 3.65 4.15 4.55 5.06 6.40
PanelB:AverageB/M,OP,Inv,andRVarcharacteristics
Small 1.01 0.96 0.93 0.90 0.94 0.24 0.28 0.33 0.28 −0.09
2 0.89 0.83 0.80 0.77 0.73 0.34 0.31 0.30 0.28 0.18
3 0.85 0.77 0.73 0.71 0.68 0.28 0.30 0.32 0.31 0.27
4 0.82 0.73 0.69 0.68 0.64 0.29 0.32 0.35 0.31 0.30
Big 0.60 0.58 0.58 0.59 0.55 0.35 0.36 0.36 0.35 0.40
Inv RVar
Small 0.11 0.14 0.17 0.21 0.22 2.05 4.64 7.54 12.94 41.16
2 0.10 0.13 0.16 0.21 0.30 1.41 2.90 4.40 6.66 16.81
3 0.10 0.12 0.14 0.18 0.29 1.14 2.23 3.35 5.03 12.50
4 0.09 0.11 0.13 0.15 0.25 1.03 1.84 2.68 3.95 9.70
Big 0.10 0.11 0.12 0.15 0.21 0.83 1.40 1.94 2.76 5.85
PanelAshowsmeansandstandarddeviationsofmonthlyexcessreturnsonvalue-weightportfoliosformed monthlyusingafirstpasssortofNYSE,AMEX,and(beginningin1973)NASDAQstocksintoSize(market capitalization)quintilesandsecond-passsortsintoquintilesofRVar(residualvariance),usingNYSEbreakpoints forbothvariables.TheRVarsortsareconditionalonSizequintile.Theintersectionsofthetwosortsproduce25
Size-RVarportfolios.Forportfoliosformedatthebeginningofmontht,Sizeisthemarketcapofastockatthe beginningoftandRVaristhevarianceofitsdailyresidualsfromtheFFthree-factormodelestimatedusing60
(withaminimum20)daysoflaggedreturns.PanelBshowstime-seriesmeansoftheportfoliobook-to-market equityratio(B/M),operatingprofitability(OP),andinvestment(Inv)forthefiscalyearendinginthecalendar yearprecedingportfolioformation,asdefinedinTable3.PanelBalsoshowsthetime-seriesaveragevaluesof
RVarusedtoformportfolioseachmonth.

RVar quintileis−0.20%permonth.ForthemiddlethreeSizequintiles,there is no clear relation between average return and volatility in the lowest four volatility quintiles, but the portfolios in the highest volatility quintile have muchloweraveragereturns. The summary tests in Table 2 say that the five-factor model provides a better description of average returns on the Size-RVar portfolios than the FF
three-factormodel.Table8showsaclearpatterninthethree-factorintercepts. In every Size quintile, the portfolios in the lowest three RVar quintiles have positivethree-factorinterceptsandtheportfoliosinthehighestRVar quintile havenegativeintercepts.Thepatternisweakformegacapsbutprogressively stronger for smaller Size quintiles.

For microcaps, the three-factor intercept for the portfolio in the lowest RVar quintile is 0.34% per month (t=5.20), and the intercept for the portfolio in the highest RVar quintile is −1.23%
(t=−7.66). Problems remain, but the five-factor model shrinks the troublesome intercepts of the three-factor model. Four of the five three-factor intercepts for portfolios in the lowest RVar quintile are more than two standard errors
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table8
Regressionsforthe25Size-RVarportfolios,July1963toDecember2014(618months)
RVar→ Low 2 3 4 High Low 2 3 4 High
PanelA:Three-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLi+eit
Small 0.34 0.31 0.13 −0.19 −1.23 5.20 4.33 1.75 −1.86 −7.66
2 0.26 0.20 0.20 0.04 −0.72 4.16 3.04 2.77 0.56 −7.16
3 0.15 0.17 0.13 0.08 −0.43 2.32 2.53 1.82 1.06 −4.58
4 0.15 0.10 0.03 0.05 −0.29 2.02 1.45 0.45 0.65 −2.87
Big 0.08 0.11 0.01 −0.06 −0.08 1.33 2.03 0.18 −1.02 −0.86
PanelB:Five-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLOt+riRMWt+ciCMAt+eit
Small 0.22 0.17 0.09 −0.08 −0.85 3.41 2.52 1.10 −0.80 −5.63
2 0.12 0.02 0.05 −0.05 −0.46 1.97 0.34 0.69 −0.66 −4.85
3 0.01 0.03 −0.03 −0.03 −0.20 0.21 0.43 −0.47 −0.42 −2.27
4 0.02 −0.06 −0.12 −0.04 −0.04 0.25 −0.86 −1.82 −0.50 −0.42
Big −0.00 −0.02 −0.10 −0.05 0.15 −0.08 −0.38 −1.91 −0.85 1.68
Small 0.72 0.99 1.10 1.15 1.12 46.57 59.76 58.42 46.41 30.55
2 0.78 1.01 1.11 1.24 1.26 53.64 69.67 69.28 68.73 54.47
3 0.78 1.00 1.10 1.20 1.25 50.88 66.65 70.02 66.09 57.16
4 0.82 1.00 1.13 1.20 1.26 46.39 62.05 70.24 64.42 54.72
Big 0.83 0.96 1.05 1.11 1.18 59.85 77.16 80.24 75.87 55.31
s t(s)
Small 0.69 0.94 1.04 1.19 1.36 31.92 40.56 39.37 34.50 26.57
2 0.56 0.77 0.85 0.94 1.10 27.27 37.81 37.55 37.12 34.05
3 0.31 0.48 0.58 0.69 0.80 14.52 23.10 26.27 27.13 26.18
4 0.10 0.19 0.25 0.32 0.50 4.10 8.41 11.13 12.21 15.49
Big −0.27 −0.25 −0.16 −0.13 0.02 −14.06 −14.08 −8.82 −6.20 0.64
Small 0.37 0.37 0.37 0.30 0.21 12.41 11.63 10.08 6.19 2.90
2 0.32 0.34 0.30 0.24 −0.08 11.27 11.99 9.56 6.71 −1.78
3 0.34 0.38 0.33 0.23 −0.16 11.19 13.13 10.59 6.52 −3.74
4 0.36 0.31 0.25 0.17 −0.16 10.50 9.76 7.99 4.56 −3.47
Big 0.14 −0.04 0.04 0.04 −0.18 5.09 −1.48 1.68 1.49 −4.30
Small 0.39 0.45 0.25 −0.09 −0.81 12.48 13.52 6.69 −1.76 −11.06
2 0.41 0.52 0.48 0.37 −0.56 13.96 17.92 14.90 10.34 −12.02
3 0.38 0.50 0.51 0.41 −0.50 12.29 16.48 16.25 11.31 −11.30
4 0.37 0.47 0.44 0.29 −0.58 10.28 14.56 13.65 7.73 −12.54
Big 0.22 0.25 0.27 0.01 −0.48 7.99 9.87 10.24 0.24 −11.35
Small 0.50 0.47 0.34 0.05 −0.24 15.09 13.26 8.36 0.99 −3.05
2 0.50 0.53 0.39 0.17 −0.51 15.79 16.86 11.07 4.38 −10.09
3 0.53 0.44 0.41 0.21 −0.53 15.99 13.63 11.91 5.40 −11.24
4 0.56 0.45 0.38 0.19 −0.50 14.44 12.84 10.82 4.71 −10.01
Big 0.23 0.17 0.17 0.01 −0.57 7.47 6.43 6.08 0.25 −12.26
TheLHSvariablesineachsetof25regressionsarethemonthlyexcessreturnsonthe25Size-RVar(residual variance)portfolios.TheRHSvariablesaretheexcessmarketreturn,RM−RF,theSizefactor,SMB,thevalue factor,HML,oritsorthogonalcounterpart,HMLO,theprofitabilityfactor,RMW,andtheinvestmentfactor,
CMA.PanelAshowsinterceptsfromtheFFthree-factormodel,andpanelBshowsfive-factorinterceptsand slopesfrom(10).

above zero. In the five-factor model only the intercept for microcaps (0.22%
per month; t=3.41) is more than two standard errors from zero. Four of the fivethree-factorinterceptsforportfoliosinthehighestRVar quintilearemore than2.8standarderrorsbelowzero.Thefive-factormodelpullsallfourofthese
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

interceptstowardzero,buttwoarestillextreme,−0.85%permonth,t=−5.63, formicrocapsand−0.46%,t=−4.85,forthesecondSizequintile.

PanelBofTable8showsthefive-factorregressionslopesforthe25SizeRVarportfolios.MarketslopesincreasestronglyfromthelowRVartothehigh
RVarportfolios.WithinSizequintiles,thereisastrongpositiverelationbetween
SMBslopeandRVar;stockswithhigherresidualreturnvolatilitybehavelike smallerstocks.ThepositivecorrelationsofRVarwithmarketandSMBslopes help explain why Size-Var and Size-RVar portfolios produce much the same resultsinourtests.Megacapsaside,HMLOslopesarestronglypositiveinthe bottom four quintiles of RVar, but microcaps aside, they turn negative in the highestRVar quintile.Inwords,lowresidualvolatilitytendstobeassociated withvalueandhighresidualvolatilitytendstobeassociatedwithgrowth.Keep in mind, however, that the average HMLO return is close to zero, so HMLO
slopesaddalmostnothingtothedescriptionofaveragereturns.

Higher five-factor market and SMB slopes for stocks with more volatile residual returns go in the wrong direction to explain the pattern in the SizeRVaraverageportfolioreturns.Theimprovementsinthedescriptionofaverage returnprovidedbythefive-factormodelcomefromitsRMW(profitability)and
CMA(investment)slopes.MajorliftingisdonebytheRMW slopes,whichare stronglypositiveinthelowerthreequintilesofRVarandstronglynegativeinthe highestRVarquintile.TheCMAslopeshaveasimilarthoughlesspronounced pattern.Thus,theimprovementsintheexplanationofaveragereturnsprovided by the five-factor model trace to the fact that the returns of low volatility stocksbehavelikethoseoffirmsthatareprofitablebutconservativeintermsof investment,whereasthereturnsofhighvolatilitystocksbehavelikethoseof firmsthatarerelativelyunprofitablebutneverthelessinvestaggressively.NovyMarx(2014)alsofindsthatprofitabilityexposuresareimportantincapturing thelowaveragereturnsofhighvolatilitystocks.(Hismodeldoesnotinclude aninvestmentfactor.)
Average values of Inv that increase with RVar (Table 7) confirm the suggestionfromtheCMAslopesthathigherresidualvolatilityisassociatedwith moreinvestment.ForstocksinthebottomtwoSizequintiles,lowerprofitability
(OP)inthehighestRVarquintileisroughlyconsistentwithlowerRMWslopes.

InthehighestthreeSizequintiles,however,averageOP showsnorelationto
RVar – another example of multivariate regression slopes that do not line up withaunivariatecharacteristic. Thefive-factormodeldoesnotcompletelycaptureaveragereturnsonthe25
Size-RVar portfolios, but its major problems are familiar. Specifically, strong negative exposures to RMW and CMA capture the low average returns of big stocks that have high RVar. But strong negative exposures to RMW and
CMAmissalargepartoftheloweraveragereturnsofhighRVarsmallstocks. SmallstockswithstrongnegativeexposurestoRMW andCMAarethelethal combination that escapes explanation in many of the sorts here and in FF
(2015). Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table9
Averageexcessreturnsandcharacteristicsofstocksinthe25Size-ACportfolios,July1963–December
2014(618months)
AC→ Low 2 3 4 High Low 2 3 4 High
Small 0.89 0.91 0.83 0.96 0.60 7.14 6.46 6.15 6.51 7.22
2 0.84 0.86 0.80 0.78 0.64 6.58 5.77 5.76 6.20 6.85
3 0.85 0.81 0.85 0.79 0.59 6.25 5.42 5.21 5.64 6.62
4 0.75 0.69 0.65 0.74 0.71 5.73 5.09 4.92 5.15 6.26
Big 0.67 0.48 0.52 0.50 0.26 5.20 4.14 4.05 4.57 5.20
PanelB:AverageB/M,OP,Inv,andACcharacteristics
Small 0.91 0.99 0.99 0.92 0.76 −0.06 0.15 0.16 0.18 0.24
2 0.75 0.85 0.79 0.74 0.62 0.19 0.22 0.24 0.25 0.44
3 0.71 0.77 0.78 0.68 0.56 0.31 0.25 0.25 0.27 0.30
4 0.65 0.75 0.74 0.63 0.51 0.33 0.27 0.27 0.30 0.41
Big 0.52 0.59 0.57 0.47 0.41 0.43 0.33 0.33 0.36 0.67
Inv AC
Small 0.09 0.15 0.16 0.18 0.31 −57.78 −2.24 1.66 6.03 50.26
2 0.14 0.16 0.18 0.18 0.32 −39.77 −2.18 1.66 5.97 47.45
3 0.15 0.16 0.15 0.18 0.31 −66.10 −2.15 1.67 5.90 38.96
4 0.13 0.12 0.14 0.16 0.25 −22.48 −2.12 1.60 5.84 22.28
Big 0.15 0.12 0.12 0.13 0.20 −16.71 −2.06 1.58 5.64 27.88
PanelAshowsmeansandstandarddeviationsofmonthlyexcessreturnson25value-weight(VW)portfolios formedyearlyattheendofJuneusingindependentsortsofNYSE,AMEX,and(beginningin1973)NASDAQ
stocksintoSize(marketcapitalization)quintilesandquintilesofAC(accruals),withNYSEbreakpointsforboth variables.ForportfoliosformedinJuneofyeart,SizeismarketcapitalizationattheendofJuneandACisthe changeinoperatingworkingcapitalpersplit-adjustedsharefromthefiscalyear-endint−2tot−1dividedby bookequitypersplit-adjustedshareint−1.PanelBshowstime-seriesmeansoftheportfoliobook-to-market equityratio(B/M),operatingprofitability(OP),andinvestment(Inv)forthefiscalyearendinginthecalendar yearprecedingportfolioformation,asdefinedinTable3.PanelBalsoshowsthetime-seriesaveragevaluesof
ACusedtoformportfolioseachyear.

6. Accruals
Panel A of Table 9 shows average excess returns on the 25 VW Size-AC
portfolios.AveragereturnsaresimilarforthelowerfourAC quintilesofeach ofthefoursmallestSizequintiles.FormegacapsthelowestAC quintilehasa higheraveragereturnthantheportfoliosinthemiddlethreequintiles.Infour of the five Size quintiles, average returns are much lower for the highestAC
quintile.ThemegacapportfoliointhehighestACquintilehasbyfarthelowest averageexcessreturninthematrix,0.26%permonth.ThereisalsoaSizeeffect ineveryAC quintile:ThemicrocapportfolioineachAC quintilehasahigher averagereturnthanthemegacapportfolio.

PanelAofTable10showsregressioninterceptsforthe25Size-ACportfolios fromtheFFthree-factormodel,thefour-factormodelthataddsCMA(thebestperformingmodelinthesummarytestsontheSize-AC portfoliosinTable2), and the five-factor model that also adds RMW. The FF three-factor model overestimates average returns on four of five portfolios in the highest AC
quintile, producing intercepts from 1.90 to 4.03 standard errors below zero. TheexceptionistheportfoliointhesecondlargestSizequintile,which,unlike
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

the other portfolios in the highest AC quintile, does not have a low average return(Table9).TheFFthree-factormodelunderestimatesaveragereturnson
19ofthe20portfoliosinthelowerfourACquintiles.Themostextremepositive intercept,0.28%permonth(t=3.32),isforthemegacapportfoliointhelowest
AC quintile.

Thefour-factormodelthataddsCMAtotheFFthree-factormodelmovesall thetroublesomenegativeinterceptsinthehighestACquintiletowardzero,and onlythoseforthetwosmallestSizequintilesaremorethantwostandarderrors fromzero.Thefour-factorinterceptforthemegacapportfoliointhelowestAC
quintileisabitlargerthanthethree-factorintercept(0.30,t=3.47,versus0.28,
Table10
Regressionsforthe25Size-ACportfolios,July1963toDecember2014(618months)
AC→ Low 2 3 4 High Low 2 3 4 High
PanelA:Regressionintercepts
Three-factor:Mkt,SMB,andHML
Small 0.02 0.12 0.06 0.16 −0.28 0.26 1.61 0.95 2.48 −4.03
2 0.02 0.12 0.06 −0.00 −0.18 0.28 1.87 0.95 −0.04 −2.86
3 0.13 0.14 0.18 0.08 −0.18 1.68 2.10 2.74 1.25 −2.21
4 0.10 0.06 0.01 0.15 0.03 1.23 0.92 0.09 2.23 0.35
Big 0.28 0.10 0.12 0.07 −0.17 3.32 1.93 2.21 1.15 −1.90
Four-factor:Mkt,SMB,HML,andCMA
Small −0.04 0.05 0.02 0.13 −0.27 −0.47 0.74 0.26 2.01 −3.96
2 0.00 0.10 0.03 −0.00 −0.15 0.07 1.53 0.42 −0.03 −2.38
3 0.13 0.12 0.16 0.10 −0.11 1.70 1.73 2.37 1.57 −1.31
4 0.08 0.02 0.02 0.13 0.07 0.95 0.32 0.24 1.97 0.87
Big 0.30 0.08 0.09 0.10 −0.11 3.47 1.52 1.70 1.67 −1.21
Five-factor:Mkt,SMB,HMLO,RMW,andCMA
Small 0.12 0.20 0.13 0.22 −0.19 1.63 3.09 2.03 3.44 −2.70
2 0.06 0.10 0.04 −0.01 −0.17 0.93 1.52 0.60 −0.10 −2.62
3 0.20 0.16 0.17 0.08 −0.19 2.45 2.31 2.53 1.18 −2.30
4 0.09 0.09 −0.02 0.12 0.07 1.06 1.29 −0.27 1.79 0.82
Big 0.35 0.10 0.04 0.05 −0.20 4.00 1.94 0.64 0.83 −2.21
PanelB:Regressionslopes
Three-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLt+eit
Small −0.02 0.00 0.02 0.00 −0.04 −0.87 0.04 0.87 0.04 −1.47
2 −0.00 0.07 0.05 0.03 −0.09 −0.14 3.12 2.32 1.18 −4.20
3 −0.07 0.02 0.08 0.06 −0.05 −2.64 0.97 3.45 2.62 −1.76
4 −0.05 0.10 0.18 −0.02 −0.13 −1.74 3.94 7.88 −0.81 −4.33
Big −0.27 −0.03 0.02 −0.10 −0.19 −8.84 −1.88 1.02 −4.34 −5.91
Four-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLt+ciCMAt+eit
Small −0.15 −0.14 −0.08 −0.06 −0.03 −4.04 −4.13 −2.54 −2.09 −1.01
2 −0.03 0.03 −0.02 0.03 −0.03 −1.04 0.83 −0.70 0.96 −1.01
3 −0.07 −0.03 0.03 0.11 0.12 −1.77 −0.95 0.98 3.49 3.01
4 −0.10 0.01 0.21 −0.05 −0.03 −2.55 0.16 6.55 −1.69 −0.86
Big −0.23 −0.08 −0.04 −0.03 −0.05 −5.76 −3.22 −1.56 −0.87 −1.23
Small 0.28 0.31 0.22 0.14 −0.01 5.07 6.25 4.81 3.18 −0.13
2 0.06 0.10 0.16 −0.01 −0.14 1.40 2.26 3.67 −0.12 −3.23
3 −0.02 0.12 0.12 −0.10 −0.38 −0.30 2.52 2.41 −2.29 −6.56
4 0.11 0.21 −0.05 0.08 −0.21 1.88 4.24 −1.01 1.63 −3.60
Big −0.08 0.10 0.14 −0.16 −0.31 −1.26 2.72 3.50 −3.61 −4.89
(continued)
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table10
Continued
AC→ Low 2 3 4 High Low 2 3 4 High
Five-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLOt+riRMWt+ciCMAt+eit
Small −0.07 −0.07 −0.03 −0.02 0.01 −2.12 −2.09 −0.85 −0.69 0.29
2 −0.00 0.03 −0.02 0.03 −0.04 −0.16 0.84 −0.50 0.86 −1.27
3 −0.04 −0.01 0.04 0.10 0.08 −0.97 −0.32 1.16 3.05 2.00
4 −0.09 0.04 0.19 −0.06 −0.04 −2.35 1.14 5.92 −1.79 −0.87
Big −0.21 −0.07 −0.07 −0.05 −0.10 −5.07 −2.70 −2.62 −1.68 −2.24
Small −0.38 −0.38 −0.27 −0.22 −0.21 −10.77 −11.64 −8.74 −7.01 −6.23
2 −0.13 0.00 −0.03 0.02 0.03 −4.22 0.04 −1.01 0.54 1.13
3 −0.16 −0.10 −0.03 0.08 0.21 −3.97 −3.01 −0.75 2.39 5.27
4 −0.05 −0.15 0.12 0.01 −0.00 −1.15 −4.49 3.74 0.28 −0.05
Big −0.17 −0.07 0.12 0.11 0.19 −3.94 −2.77 4.57 3.61 4.40
Small 0.04 0.09 0.08 0.03 −0.09 1.08 2.54 2.46 0.95 −2.40
2 0.00 0.13 0.14 0.03 −0.16 0.05 3.69 3.99 0.79 −4.88
3 −0.12 0.07 0.14 0.02 −0.21 −2.80 1.85 3.85 0.55 −4.96
4 −0.00 0.18 0.18 0.03 −0.25 −0.01 4.83 5.20 0.71 −5.48
Big −0.35 0.00 0.12 −0.16 −0.32 −7.55 0.16 4.25 −4.79 −6.68
TheLHSvariablesineachsetof25regressionsarethemonthlyexcessreturnsonthe25Size-AC(accruals)
portfoliosofTable2.TheRHSvariablesaretheexcessmarketreturn,Mkt=RM−RF,theSizefactor,SMB,the valuefactor,HML,oritsorthogonalcounterpart,HMLO,theprofitabilityfactor,RMW,andtheinvestmentfactor,
CMA.PanelAshowsthree-factor,four-factor,andfive-factorregressionintercepts.PanelBshowsregression slopesforRMW,CMA,andHMLorHMLO(asrelevant).

t=3.32),butmostoftheinterceptsinthefirstfourquintilesofAC moveabit towardzero. Performancedeterioratesinthefive-factormodelthataddsRMW,especially for microcaps.Adding RMW pushes the intercept for the microcap portfolio in the highestAC quintile toward zero (from −0.27, t=−3.96, to −0.19, t=
−2.70),butitmovestheinterceptsfortheotherfourmicrocapportfoliosfrom valuesmostlyindistinguishablefromzerotolargepositivevaluesthatare1.63
to3.44standarderrorsfromzero.Theproblemsofthefive-factormodelarenot limitedtomicrocaps.AddingRMW increasestheinterceptsforallportfolios inthelowestAC quintile,andthreeofthefiveinterceptsfortheportfoliosin thehighestAC quintilebecomemorenegative. TheregressionslopesinpanelBofTable10helpusinterprettheintercepts.

(WedonotshowR M −R F andSMBslopessincetheyaresimilarfordifferent models.)ForthetroublesomeportfoliosinthethreesmallestSizequintilesand thehighestACquintile,theHMLslopesintheFFthree-factormodelarecloseto zero,soHMLdoesnothelpexplainthelowaveragereturnsoftheseportfolios. TheHML slopeforthemegacapportfoliointhehighestAC quintileisrather stronglynegative,whichhelpsexplaintheextremelylowaverageexcessreturn onthisportfolio,0.26%permonth(Table9),butneverthelessleavesathreefactor intercept, −0.17% per month that is −1.90 standard errors from zero
(Table10).ThenegativeHMLslopeforthemegacapportfoliointhelowestAC
quintileinpartexplainswhythethree-factormodeldoesapoorjobexplaining thehighaveragereturnofthisportfolio. Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Microcapsaside,thefour-factormodelthataddsCMAtotheFFthree-factor model produces strong negative CMA slopes for the portfolios in the highest
AC quintile in Table 10. This is consistent with the Inv evidence in Table 9
that firms in these portfolios tend to invest aggressively, and it helps explain whythismodelimprovestheregressioninterceptsfortheseportfolios.Table9
showsthemicrocapportfoliointhehighestAC quintilealsoinvestsalot,but itsCMAslopeisclosetozeroanditsfour-factorintercept,−0.27(t=−3.96), isalmostunchangedfromthethree-factorintercept,−0.28.MostofthefourfactorHMLslopesareclosetozeroandsohavelittleeffectontheregression intercepts. TheRMWslopesformicrocapsinthefive-factormodelarestronglynegative.

This is consistent with the evidence in Table 9 that controlling for AC, profitabilityislowestformicrocaps.DrivenbyalargenegativeRMW slope, the intercept for the microcap portfolio in the highest AC quintile shrinks from −0.27 in the four-factor model that does not include RMW to −0.19
(t=−2.70)inthefive-factormodel.TheRMWslopesare,however,alsolargely responsibleforthegeneraldeteriorationoftheinterceptsfromthefour-factor tothefive-factormodelfortheotherfourmicrocapportfolios.Thereductions predicted by negative RMW slopes do not show up in the average returns of theseportfolios.NegativeRMW slopesforportfoliosinthelowestACquintile
(whichdonothavelowaveragereturnsinTable9)andpositiveslopesforsome oftheportfoliosinthehighestAC quintile(whichhavelowaveragereturns)
areresponsibleforthefive-factormodel’sadverseeffectontheinterceptsfor theseportfolios.

FF(2015)findthatin5×5sortsonSizeandInv,theportfoliosinthesmaller
SizequintilesandthehighestInvquintileproduceinterceptproblems,evenfor asset pricing models that include the investment factor CMA. This suggests that small firms that invest a lot are a general problem for the asset pricing modelsweconsider.Table9showsthesefirmsareprominentinthehighestAC
portfoliosofsmallerSizequintiles,andtheinterceptsfortheseportfoliosare alwaysamongthemostextremeinTable10. TheSize-AC portfoliosprovideavaluablecaution.Theyaretheonlysorts, hereandinFF(2015),inwhichthefive-factormodelperformsnoticeablyworse than other models.

It is also noteworthy that the problems of the five-factor modelintheSize-AC sortstracetotheprofitabilityfactorsinceinothersorts
RMWtypicallyimprovesthedescriptionofaveragereturns,oftensubstantially. 7. Momentum
Table11showsaverageexcessreturnsformonthlyindependentsortsofstocks intoquintilesofSizeandmomentum(Prior2–12).Withoneexception,there isaSizeeffectinthePrior2–12quintiles;givenPrior2–12,averagereturns arelargerforportfoliosofsmallstocks.TheexceptionisthelowestPrior2–
12 quintile (extreme losers), in which the portfolios in the two smallest Size
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table11
Averageexcessreturnsandcharacteristicsofstocksinthe25Size-Prior2–12portfolios,July
1963–December2014(618months)
Prior2–12→ Low 2 3 4 High Low 2 3 4 High
Small 0.03 0.67 0.91 1.05 1.39 8.01 5.88 5.43 5.50 6.78
2 0.14 0.66 0.82 1.01 1.23 7.86 5.88 5.27 5.41 6.74
3 0.27 0.62 0.72 0.78 1.19 7.37 5.53 5.07 5.00 6.31
4 0.20 0.59 0.66 0.79 1.04 7.26 5.52 4.87 4.79 5.89
Big 0.17 0.46 0.39 0.55 0.79 6.79 4.88 4.37 4.31 5.26
PanelB:AverageB/M,OP,Inv,andPrior2–12characteristics
Small 0.84 0.95 0.98 1.00 0.99 0.08 0.21 0.28 0.28 0.17
2 0.72 0.80 0.83 0.84 0.82 0.24 0.27 0.28 0.29 0.24
3 0.68 0.75 0.78 0.78 0.73 0.27 0.29 0.29 0.29 0.29
4 0.66 0.71 0.74 0.73 0.71 0.29 0.35 0.33 0.30 0.28
Big 0.56 0.59 0.60 0.60 0.61 0.36 0.34 0.35 0.37 0.39
Inv Prior2–12
Small 0.24 0.14 0.13 0.13 0.14 −31.87 −4.56 9.45 25.08 90.33
2 0.27 0.16 0.15 0.15 0.19 −27.79 −4.33 9.55 25.08 83.61
3 0.24 0.15 0.14 0.14 0.20 −25.91 −4.13 9.56 24.97 77.08
4 0.19 0.14 0.12 0.13 0.18 −23.80 −4.03 9.66 24.90 71.41
Big 0.19 0.13 0.12 0.12 0.16 −20.94 −3.71 9.68 24.82 58.96
PanelAshowsmeansandstandarddeviationsofmonthlyexcessreturnsonvalue-weightportfoliosformed monthlyusingindependentsortsofNYSE,AMEX,and(beginningin1973)NASDAQstocksintoSize(market capitalization)quintilesandquintilesofPrior2–12(momentum),withNYSEbreakpointsforbothvariables.

Theintersectionsofthetwosortsproduce25Size-Prior2–12portfolios.Forportfoliosformedatthebeginning ofmontht,SizeisthemarketcapofastockatthebeginningoftandPrior2–12isitscumulativereturnfor the11monthsfromt−12tot−2.PanelBshowstime-seriesmeansoftheportfoliobook-to-marketequityratio
(B/M),operatingprofitability(OP),andinvestment(Inv)forthefiscalyearendinginthecalendaryearpreceding portfolioformation,asdefinedinTable3.PanelBalsoshowsthetime-seriesaveragevaluesofPrior2–12used toformportfolioseachmonth. quintileshaveextremelowaverageexcessreturns,0.03%and0.14%permonth.

There is a strong momentum effect in every Size quintile, but it decreases as
Sizeincreases.Thespreadinaveragereturnsfromextremewinnerstoextreme losersis1.36%permonthformicrocapsand0.62%formegacaps.Theaverage monthlyexcessreturnformicrocapextremewinnersis1.39%,versus0.79%
formegacapwinners. Table12showsinterceptsfromthefive-factormodel(3)andthesix-factor modelthataddsMOM to(10)andinwhichHMLOisthesumoftheintercept
(0.04; t=0.52) and residual from the regression of HML on R M −R F, SMB,
RMW,CMA,andMOM.Thefive-factormodelisnotmuchhelpincapturing the average returns produced by momentum sorts.

The five-factor intercepts forextremelosersarestronglynegative,theinterceptsforextremewinnersare stronglypositive,andthespreadsbetweentheinterceptsforextremewinners andlosersaresimilartothespreadsinaveragereturns. In the dividend discount model (2) that Fama and French (2015) use to motivatethefive-factormodel,theinternalrateofreturnonexpectedcashflows to shareholders (r in Equation (2)) is approximately the long-term expected stock return. Momentum is short-term; the relative performance of stocks in
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Table12
Regressionsforthe25Size-Prior2–12portfolios,July1963–December2014(618months)
Prior2–12→ Low 2 3 4 High Low 2 3 4 High
PanelA:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLt+riRMWt+ciCMAt+eit
Small −0.71 −0.20 0.02 0.20 0.62 −4.68 −2.50 0.39 3.06 6.40
2 −0.62 −0.21 −0.05 0.15 0.51 −4.35 −2.58 −0.80 2.79 5.63
3 −0.37 −0.18 −0.11 −0.07 0.52 −2.40 −2.10 −1.75 −1.06 5.34
4 −0.40 −0.21 −0.13 0.02 0.44 −2.41 −2.19 −1.94 0.34 4.09
Big −0.37 −0.13 −0.17 −0.04 0.33 −2.27 −1.29 −2.72 −0.62 3.08
PanelB:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLOt+riRMWt+ciCMAt+miMOMt+eit
Small −0.23 −0.01 0.09 0.15 0.40 −2.28 −0.09 1.44 2.31 4.85
2 −0.11 0.03 0.01 0.10 0.24 −1.47 0.45 0.09 1.88 3.73
3 0.16 0.06 −0.00 −0.13 0.22 1.79 0.98 −0.02 −2.11 3.30
4 0.16 0.07 −0.02 −0.03 0.11 1.60 1.09 −0.25 −0.45 1.49
Big 0.17 0.19 −0.09 −0.15 −0.02 1.59 2.76 −1.51 −2.61 −0.24
Small 0.13 0.29 0.31 0.21 0.05 2.62 9.20 10.27 6.55 1.37
2 0.06 0.20 0.25 0.21 0.01 1.66 7.00 8.92 8.33 0.36
3 0.05 0.21 0.27 0.29 0.00 1.07 6.84 9.51 9.87 0.14
4 0.09 0.14 0.24 0.20 0.04 1.94 4.26 7.90 6.68 1.03
Big 0.02 0.04 0.13 0.08 0.06 0.34 1.20 4.28 2.64 1.73
Small −0.31 0.15 0.26 0.15 −0.17 −6.37 4.75 8.62 4.70 −4.22
2 −0.16 0.27 0.30 0.22 −0.15 −4.50 9.34 11.03 8.68 −4.87
3 −0.18 0.26 0.34 0.37 −0.08 −4.16 8.46 11.84 12.48 −2.44
4 −0.20 0.29 0.37 0.36 −0.09 −4.05 8.74 12.31 11.64 −2.63
Big 0.03 0.24 0.26 0.25 −0.01 0.55 7.43 8.80 8.89 −0.27
Small −0.10 0.33 0.38 0.33 0.02 −1.86 9.81 11.67 9.57 0.38
2 −0.17 0.23 0.32 0.30 −0.13 −4.49 7.44 10.69 10.78 −3.89
3 −0.18 0.22 0.33 0.35 −0.14 −3.84 6.61 10.68 10.91 −3.93
4 −0.09 0.30 0.34 0.30 −0.10 −1.69 8.47 10.42 8.95 −2.46
Big −0.13 0.19 0.15 0.22 −0.17 −2.34 5.47 4.72 7.25 −4.75
m t(m)
Small −0.69 −0.30 −0.12 0.05 0.30 −31.07 −20.38 −8.90 3.09 16.16
2 −0.72 −0.35 −0.10 0.04 0.37 −43.43 −26.44 −7.75 3.76 25.35
3 −0.74 −0.36 −0.18 0.05 0.41 −36.98 −25.21 −13.92 4.00 27.62
4 −0.79 −0.41 −0.19 0.05 0.45 −35.34 −26.70 −13.35 3.28 27.17
Big −0.75 −0.45 −0.13 0.15 0.48 −32.18 −29.29 −9.08 11.34 30.72
TheLHSvariablesarethemonthlyexcessreturnsonthe25Size-Prior2–12portfolios.TheRHSvariablesare theexcessmarketreturn,RM−RF,theSizefactor,SMB,thevaluefactor,HML,oritsorthogonalcounterpart,
HMLO,theprofitabilityfactor,RMW,theinvestmentfactor,CMA,andthemomentumfactorMOM,constructed usingindependent2x3sortsonSizeandeachofB/M,OP,Inv,andPrior2–12.Thetableshowsinterceptsfor afive-factormodelthatdoesnotincludeMOM,andinterceptsandslopesforthesix-factormodelthatincludes
MOM.Inthistable,HMLOisthesumoftheintercept(0.04,t=0.51)andtheresidualfromtheregressionof
HMLonRM−RF,SMB,HML,RMW,CMA,andMOM.

months t−12 to t−2 tends to persist for only about nine months starting in t.Becauseofthelong-termreturnreversalsidentifiedbyDeBondtandThaler
(1985),Prior2–12isnegativelyrelatedtolonger-termrelativereturns.Thus, perhapsitisnotsurprisingthatthefive-factormodel,whichistargetedatlongrunexpectedreturns,failstocapturethepositiverelationbetweenPrior2–12
andcurrentreturns. Adding MOM to the five-factor model improves the regression intercepts, but problems remain. Most noticeable is the unexplained momentum among
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

microcaps: the extreme loser portfolio has a rather strong negative intercept,
−0.23% per month (t=−2.28), the winner portfolio has a strong positive intercept, 0.40% (t=4.85), and the intercepts increase monotonically from losers to winners. There is a weaker momentum pattern in the intercepts of thesecondSizequintile,andthereisaweakreversemomentumpatterninthe interceptsforthelargest(megacap)quintile.

Theregressionslopesforthesix-factormodelshowwhyincludingMOMis criticalinthetestsontheSize-Prior2–12portfolios.TheMOMslopesincrease fromstronglynegativeforloserstostronglypositiveforwinners,whichisthe patterninaveragereturns.ButHMLO,RMW,andCMAprovidelittlehelp.Both theHMLOpremiumandtheHMLOslopesforextremewinnersandextreme losersareclosetozero.Megacapsaside,RMW slopesarenegativeforextreme losers,andthenegativeslopesarehelpfulforexplaininglowaveragereturns, but RMW slopes are also slightly negative for extreme winners. The CMA
slopeshaveasimilarpattern.PanelBofTable11showstherearealsonoclear patternsinB/M,OP,andInvforthe25Size-Prior2–12portfolios. 8.

Conclusions
Thelistofanomaliesshrinksinthefive-factormodel,inpartbecauseanomalous returnsbecomelessanomalousandinpartbecausethereturnsassociatedwith differentanomalyvariablessharefactorexposuresthatsuggesttheyareinlarge partthesamephenomenon. Theflatrelationbetweenmarketβandaveragereturnthathaslongplagued testsoftheCAPMiscapturedinthefive-factormodelbyRMWandCMAslopes that offset the average return predictions of market and SMB slopes.

Stocks withhigherCAPMmarketβshavehigherfive-factormarketandSMBslopes thatraisepredictionsoftheiraveragereturns.Butlowβ stockshavepositive exposures to the profitability and investment factors of the five-factor model thatraisepredictionsoftheiraveragereturns,andhighβ stockshavenegative exposures to RMW and CMA that lower their predicted returns.Thus, low β
stock returns behave like those of profitable firms that invest conservatively, whereas high β returns behave like those of less profitable firms that invest aggressively.

The high average returns associated with share repurchases, which are a problemfortheFFthree-factormodel,ceasetobeananomalyinthefive-factor model.Thereasonagainisthatthereturnsofrepurchasersbehavelikethose ofprofitablefirmsthatinvestconservatively.PositiveexposurestoRMW and
CMAalsogoalongwaytowardcapturingtheaveragereturnsoflowvolatility stocks,whethervolatilityismeasuredintermsoftotalreturnsorresidualsfrom theFFthree-factormodel. Likethereturnsofrelativelyunprofitablefirmsthatinvestaggressively,the returnsofhighβstocks,stockswithhighlyvolatilereturns,andstocksoffirms that make large share issues load negatively on RMW and CMA. Unlike the
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

averagereturnsofhighβ portfolios,however,negativefive-factorexposures toRMW andCMAdonotfullycapturethelowaveragereturnsassociatedwith largeshareissuesandhighvolatility.Unexplainedaveragereturnsarelargely concentratedinsmallstocks,especiallymicrocaps.Smallstockswithnegative exposures to RMW and CMA are also a problem for the five-factor model in manyofthetestsinFF(2015),leadingthemtodubitthelethalcombination. The five-factor model typically performs better than the FF three-factor modelwhenappliedtodifferentsetsofLHSportfolioshereandinFF(2015). PortfoliosformedonSizeandaccrualsareanexception.Thepricingproblems associated with accruals do not seem to have much to do with the lethal combinationofslopesthatisacommonprobleminothersorts.

All models that do not include a momentum factor fare poorly in the tests on the 25 Size-Prior 2–12 portfolios.Asix-factor model that includes MOM
performswell,butbyplayingahomegame;themomentumfactor,MOM,is justacoarse(2×3ratherthan5×5)versionofthesortsusedtoconstructthe
25Size-Prior2–12portfolios.Nevertheless,thesix-factormodelleaveslotsof momentuminmicrocapreturnsunexplained.

TableA1
Summarystatisticsforthe25Size-Varportfolios,July1963–December2014(618months)
Var→ Low 2 3 4 High Low 2 3 4 High
Small 1.00 1.18 1.09 0.81 −0.18 4.07 5.67 6.50 7.53 9.22
2 0.90 1.03 1.06 0.91 0.27 4.02 5.26 5.90 6.83 8.78
3 0.75 0.85 0.97 0.88 0.44 3.68 4.78 5.39 6.23 8.08
4 0.67 0.74 0.77 0.77 0.49 3.72 4.48 5.10 5.79 7.69
Big 0.43 0.53 0.54 0.46 0.46 3.43 3.99 4.48 5.10 6.74
PanelB:AverageB/M,OP,Inv,andVarcharacteristics
Small 1.01 0.96 0.93 0.90 0.94 0.24 0.28 0.33 0.30 −0.10
2 0.89 0.83 0.80 0.78 0.73 0.34 0.31 0.30 0.29 0.18
3 0.84 0.77 0.73 0.72 0.68 0.29 0.30 0.31 0.31 0.27
4 0.81 0.72 0.69 0.68 0.65 0.29 0.33 0.35 0.31 0.30
Big 0.65 0.55 0.56 0.58 0.57 0.34 0.37 0.36 0.36 0.37
Inv Var
Small 0.11 0.14 0.17 0.21 0.22 2.53 5.69 9.01 14.88 43.98
2 0.10 0.13 0.16 0.21 0.30 1.89 3.79 5.70 8.52 20.08
3 0.10 0.12 0.14 0.18 0.30 1.54 2.98 4.47 6.69 15.70
4 0.10 0.11 0.12 0.15 0.26 1.41 2.52 3.70 5.43 12.57
Big 0.10 0.11 0.12 0.14 0.21 1.33 2.16 2.98 4.19 8.51
Thistableshowsmeansandstandarddeviationsofmonthlyexcessreturnsonvalue-weightportfoliosformed monthlyusingafirstpasssortofNYSE,AMEX,and(beginningin1973)NASDAQstocksintoSize(market capitalization)quintilesandsecond-passsortsintoquintilesofVar(totalvariance)usingNYSEbreakpoints forbothvariables.TheVarsortsareconditionalonSizequintile.Theintersectionsofthetwosortsproduce25
Size-Varportfolios.Forportfoliosformedatthebeginningofmontht,Sizeisthemarketcapofastockatthe beginningoftandVaristhevarianceofitsdailyreturnsestimatedusing60(withaminimum20)daysoflagged returns.PanelAshowsmeansandstandarddeviationsofmonthlyexcessreturnsonthe25portfolios.Panel
Bshowstime-seriesmeansoftheportfoliobook-to-marketequityratio(B/M),operatingprofitability(OP), andinvestment(Inv)forthefiscalyearendinginthecalendaryearprecedingportfolioformation,asdefinedin
Table3.PanelBalsoshowsthetime-seriesaveragevaluesofVarusedtoformportfolioseachmonth.

Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

TableA2
Regressionsforthe25Size-Varportfolios,July1963toDecember2014(618months)
Var→ Low 2 3 4 High Low 2 3 4 High
PanelA:Three-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLt+eit
Small 0.35 0.30 0.13 −0.22 −1.25 5.34 4.09 1.68 −2.33 −7.64
2 0.27 0.21 0.18 −0.03 −0.68 4.24 3.05 2.51 −0.38 −6.08
3 0.18 0.11 0.18 0.01 −0.38 2.68 1.69 2.36 0.08 −3.76
4 0.13 0.10 0.06 0.00 −0.26 1.68 1.31 0.83 0.06 −2.46
Big 0.05 0.11 0.05 −0.06 −0.12 0.73 1.85 0.89 −1.06 −1.21
PanelB:Five-factor:Rit–RFt=ai+bi(RMt–RFt)+siSMBt+hiHMLOt+riRMWt+ciCMAt+eit
Small 0.23 0.17 0.07 −0.14 −0.87 3.65 2.42 0.95 −1.42 −5.62
2 0.12 0.03 0.04 −0.15 −0.42 2.02 0.48 0.55 −1.97 −3.96
3 0.04 −0.02 0.02 −0.14 −0.16 0.61 −0.34 0.23 −1.87 −1.60
4 0.01 −0.06 −0.11 −0.10 −0.01 0.08 −0.90 −1.67 −1.20 −0.07
Big −0.04 −0.05 −0.06 −0.11 0.13 −0.57 −0.91 −1.11 −1.69 1.30
Small 0.69 0.99 1.10 1.17 1.16 44.19 58.48 57.56 50.14 30.95
2 0.76 1.00 1.10 1.24 1.32 51.99 66.59 68.05 69.30 50.63
3 0.75 0.98 1.09 1.22 1.30 47.76 65.14 65.50 67.60 55.13
4 0.78 0.98 1.12 1.22 1.32 41.83 57.53 67.74 62.51 54.81
Big 0.76 0.93 1.03 1.14 1.24 44.97 70.40 75.24 74.54 52.07
s t(s)
Small 0.67 0.94 1.05 1.20 1.39 30.34 39.61 39.38 36.69 26.31
2 0.55 0.76 0.84 0.96 1.13 26.85 35.93 36.90 38.19 30.80
3 0.31 0.48 0.56 0.70 0.83 13.94 22.66 24.23 27.56 25.19
4 0.09 0.20 0.25 0.32 0.51 3.55 8.30 10.71 11.66 15.09
Big −0.25 −0.22 −0.17 −0.18 0.01 −10.54 −12.08 −8.84 −8.35 0.38
Small 0.35 0.42 0.39 0.33 0.24 11.30 12.68 10.54 7.29 3.21
2 0.30 0.36 0.33 0.25 −0.07 10.48 12.43 10.49 7.00 −1.33
3 0.31 0.38 0.34 0.26 −0.17 10.13 13.09 10.57 7.34 −3.62
4 0.36 0.30 0.27 0.21 −0.17 9.78 9.01 8.30 5.62 −3.59
Big 0.16 0.06 0.07 −0.02 −0.09 4.94 2.25 2.51 −0.57 −1.83
Small 0.37 0.44 0.27 −0.04 −0.79 11.74 12.97 7.04 −0.86 −10.52
2 0.40 0.52 0.47 0.43 −0.54 13.78 17.39 14.46 11.85 −10.24
3 0.38 0.45 0.54 0.47 −0.47 12.06 14.98 16.05 12.80 −9.96
4 0.36 0.45 0.50 0.33 −0.57 9.60 13.17 15.05 8.42 −11.80
Big 0.19 0.38 0.30 0.09 −0.46 5.66 14.31 11.11 2.85 −9.69
Small 0.47 0.50 0.39 0.13 −0.23 13.72 13.60 9.30 2.61 −2.84
2 0.49 0.54 0.40 0.22 −0.47 15.44 16.63 11.41 5.56 −8.32
3 0.50 0.45 0.40 0.32 −0.55 14.79 13.94 11.20 8.08 −10.69
4 0.52 0.47 0.42 0.26 −0.52 12.85 12.71 11.66 6.04 −10.06
Big 0.35 0.24 0.16 0.04 −0.59 9.66 8.51 5.34 1.12 −11.51
TheLHSvariablesineachsetof25regressionsarethemonthlyexcessreturnsonthe25Size-Var(totalvariance)
portfolios.TheRHSvariablesaretheexcessmarketreturn,RM−RF,theSizefactor,SMB,thevaluefactor,
HML,oritsorthogonalcounterpart,HMLO,theprofitabilityfactor,RMW,andtheinvestmentfactor,CMA.Panel
AshowsinterceptsfromtheFFthree-factormodel,andpanelBshowsfive-factorinterceptsandslopesfrom
(10).

Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

References
Ang,A.,R.J.Hodrick,J.Xing,andX.Zhang.2006.Thecross-sectionofvolatilityandexpectedreturns.Journal ofFinance51:259–99. Barillas,F.,andJ.Shanken.2015.Whichalpha?Manuscript,GoizuetaBusinessSchool,EmoryUniversity. Black,F.,M.C.Jensen,andM.Scholes.1972.Thecapitalassetpricingmodel:Someempiricaltests.InStudies inthetheoryofcapitalmarkets,79–121.Ed.M.C.Jensen.NewYork:Praeger. Carhart,M.M.1997.Onpersistenceinmutualfundperformance.JournalofFinance52:57–82. Davis,J.L.,E.F.Fama,andK.R.French.2000.Characteristics,covariances,andaveragereturns:1929–97. JournalofFinance55:389–406. DeBondt,W.F.M.,andR.Thaler.1985.Doesthestockmarketoverreact?JournalofFinance40:793–805. Fama,E.F.1996.Multifactorportfolioefficiencyandmultifactorassetpricing. JournalofFinancialand
QuantitativeAnalysis31:441–65.

———.1998.DeterminingthenumberofpricedstatevariablesintheICAPM.JournalofFinancialand
QuantitativeAnalysis33:217–31. Fama,E.F.,andK.R.French.1993.Commonriskfactorsinthereturnsonstocksandbonds.JournalofFinancial
Economics33:3–56. ———.2012.Size,value,andmomentumininternationalstockreturns.JournalofFinancialEconomics
105:457–72. ———.2015.Afive-factorassetpricingmodel.JournalofFinancialEconomics116:1–22. Fama,E.F.,andJ.D.MacBeth.1973.Risk,return,andequilibrium:Empiricaltests.JournalofPoliticalEconomy
81:607–36. Frazzini,A.,andL.H.Pedersen.2014.Bettingagainstbeta.JournalofFinancialEconomics111:1–25. Gibbons,M.R.,S.A.Ross,andJ.Shanken.1989.Atestoftheefficiencyofagivenportfolio.Econometrica
57:1121–52.

Harvey,C.R.,Y.Liu,andH.Zhu.2015....andthecross-sectionofexpectedreturns.ReviewofFinancialStudies
29:5–68. Hou,K.,C.Xue,andL.Zhang.2015.Digestinganomalies:Aninvestmentapproach.ReviewofFinancialStudies
28:650–705. Ikenberry,D.,J.Lakonishok,andT.Vermaelen.1995.Marketunderreactiontoopenmarketsharerepurchases. JournalofFinancialEconomics39:181–208. Jegadeesh,N.,andS.Titman.1993.Returnstobuyingwinnersandsellinglosers:Implicationsforstockmarket efficiency.JournalofFinance48:65–91. Lewellen,J.,S.Nagel,andJ.Shanken.2010.Askepticalappraisalofassetpricingtests.JournalofFinancial
Economics96:175–94. Lintner,J.1965.Thevaluationofriskassetsandtheselectionofriskyinvestmentsinstockportfoliosandcapital budgets.ReviewofEconomicsandStatistics47:13–37.

Loughran,T.,andJ.R.Ritter.1995.Thenewissuespuzzle.JournalofFinance50:23–51. Loughran,T.,andA.M.Vijh.1997.Dolong-termshareholdersbenefitfromcorporateacquisitions?Journalof
Finance52:1765–90. Merton,R.1973.Anintertemporalassetpricingmodel.Econometrica41:867–77. Miller,M.,andF.Modigliani.1961.Dividendpolicy,growth,andthevaluationofshares.JournalofBusiness
34:411–33. Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682

Novy-Marx, R. 2014. Understanding defensive equity. Manuscript, Simon Graduate School of Business,
UniversityofRochester,September.
Pástor,L’.,andR.F.Stambaugh.2003.Liquidityriskandexpectedstockreturns.JournalofPoliticalEconomy
111:642–85.
Sharpe,W.F.1964.Capitalassetprices:Atheoryofmarketequilibriumunderconditionsofrisk.Journalof
Finance19:425–42.
Sloan,R.G.1996.Dostockpricesfullyreflectinformationinaccrualsandcashflowsaboutfutureearnings?
TheAccountingReview71:289–315.
Downloaded from https://academic.oup.com/rfs/article-abstract/29/1/69/1843682
