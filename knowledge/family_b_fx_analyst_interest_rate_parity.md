---
family: B
source: fx analyst interest rate parity
doc_type: pdf
reliability: 95
tickers: []
ingested: 2026-06-27
---

Chapter 6
Interest Rate Parity
© 2018 Cambridge University Press 6-1

• The intuition behind interest rate parity
• Future value of one unit of currency depends on interest rate for that currency
• Interest rate parity
• Equality of returns on comparable money market assets when the forward foreign exchange market is used to eliminate foreign exchange risk
• Relationship between forward/spot rates and the interest rate differential between two countries
• Why there must be interest rate parity h ff
FF(h/ff)/SS(h/ff) = (1 + ii )/(1 + ii )
• If not, arbitrage possibilities would exist (borrowing any government controls)
© 2018 Cambridge University Press 6-2

Consider a swap, as in our homework.
Suppose that an investor that has dollars buys pounds on the spot market at a rate of S dollars per pound. Simultaneously, he sells those pounds forward for F
dollars per pound.
What if F < S? Why would the investor buy pounds for ninety days and then sell them back for fewer dollars. He would if he knew he could earn a higher interest rate on a ninety-day pound deposit compared to a 90-day dollar deposit: i£ > i$
Similarly the counterparty accepting dollars for 90 days earns more pounds when he sells dollars on the forward market than he has to pay to buy the dollars:
1/F > 1/S.
He comes out ahead in the foreign exchange market, but earns less interest.
© 2018 Cambridge University Press 6-3

• $10M to invest, iUS = 8%; iUK = 12%; S = $1.60/£; F1-year = $1.53/£
• Steps:
• Convert using spot rate:
• Invest at foreign interest rate:
$10MM ÷ ($1.60/£) = £6.25MM
• Convert back at forward rate:
£6.25MM × 1.12 = £7MM
• Compare to what you could have earned by just investing in your home nation:
£7MM × ($1.53/£) = $10.71MM
• Investing at home (U.S.) is more profitable for Kevin.
$10MM × (1 + 0.08) = $10.8MM
• But then Kevin and everyone else would want to invest in the U.S. Interest rates would fall in the U.S., and rise in the U.K.
• Also, fewer people would buy pounds on the spot market and fewer would sell pounds on the forward market.
© 2018 Cambridge University Press 6-4

• $10M to invest, iUS = 8%; iUK = 12%; S = $1.60/£; F1-year = $1.53/£
• Steps:
• Borrow pounds: (what Kevin owes at end of investment term)
• Convert pounds to dollars:
£1MM × 1.12 = £1.12MM
• Invest at U.S. interest rate:
£1 MM × ($1.60/£) = $1.6MM
• Convert back at forward rate:
£1.6MM × 1.08 = $1.728MM
• Kevin would make £9,411.76 (Step 4 – Step 1) profit for every £1M that is
$1.728MM × ($1.53/£) = £1,129,411.76
borrowed!
© 2018 Cambridge University Press 6-5

• Suppose I have $1000 to invest now.
• I can invest it in U.S. dollar assets, and at the end of the period, I will have
$1000 x 1+ i$
• Or, I could take the $1000 and buy $1000/S pounds.
$/£
• I then take those pounds and invest them in pound assets. At the end of the period, I
will have ($1000/S )x(1+ i£) pounds.
$/£
• Knowing that I will have that many pounds at the end of the period, today I make a contract to sell ($1000/S )x(1+ i£) pounds forward at a rate of F .
$/£ $/£
• I will have $1000(F /S )x(1+ i£) in dollars at the end of the period.
$/£ $/£
• Since there is no uncertainty in either investment, arbitrage tells us
1+ i$ = (F /S )x(1+ i£)
$/£ $/£
© 2018 Cambridge University Press 6-6

• Deriving interest rate parity
• When the forward rate is priced correctly, an investor is indifferent between investing at home or abroad
• General expression for interest rate parity
• Interest rate parity and forward premiums and discounts
[1 + ii] = [1/SS] × [1 + ii ∗] × FF
• Subtracting 1 from each side and simplifying we obtain
(1 + ii)/(1 + ii ∗) = FF/SS
• If this equation is (+), the forward is selling at a premium
(ii − ii ∗)/(1 + ii ∗) = (FF − SS)/SS
• If it is (-), the forward is selling at a discount
• With continuously compounded interest rates
(ii − ii ∗) = ln(FF) − ln(SS)
© 2018 Cambridge University Press 6-7

Taking bid and ask rates into account
Is there really money to be made if CIP fails?
Suppose we have $1000. What really are our opportunities?
First, recognize that i$,bid < i$,ask . That is, the rate we borrow at is greater than the rate we get for a deposit at the bank.
Likewise, i£,bid < i£,ask .
Also, we know S < S . And, of course, F < F .
$/£, bid $/£,ask $/£, bid $/£,ask
© 2018 Cambridge University Press 6-8

We can take our $1000 and invest and earn $1000 x 1+ i$,bid
Or we can buy pounds, invest those pounds, and sell back the pounds we will have at the end of the period and earn 1000(F /S )x(1+ i£,bid) .
What if 1+ i$,bid < (F /S )x(1+ i£,bid) ? Is there necessarily a failure of arbitrage?
The cost of borrowing dollars is 1+ i$,ask . To arbitrage, we would need to borrow in dollars, buy the pounds, invest in pounds and sell the proceeds forward. We need:
1+ i$,ask < (F /S )x(1+ i£,bid)
That inequality may not be true, even if the first one is!
© 2018 Cambridge University Press 6-9

In other words, the absence of arbitrage opportunities from borrowing in dollars, and swapping the dollars for pounds requires:
1+ i$,ask >= (F /S )x(1+ i£,bid) .
Similarly, the absence of arbitrage opportunities from borrowing in pounds, and swapping the pounds for dollars, requires that:
1+ i£,ask >= (S /F )x(1+ i$,bid) .
If a researcher concludes that covered interest parity fails, one of these two conditions must fail.
© 2018 Cambridge University Press 6-10

6.2 Covered Interest Rate Parity in Practice
• Does covered interest rate parity hold?
• Prior to 2007, documented violations of interest rate parity were very rare
• Akram, Rime, and Sarno (2008) – multiple short-lived deviations that persist for only a few minutes
• Frequency, size and duration of apparent arbitrage opportunities do increase with market volatility
• 2007-2009 financial crisis
© 2018 Cambridge University Press 6-11

6.3 Why Deviations from Interest Rate Parity May
Seem to Exist
• Too good to be true?
• Default risks
• Risk that one of the counterparties may fail to honor its contract
• Exchange controls
• Limitations
• Taxes
• Political risk
• A crisis in a country could cause its government to restrict any exchange of the local currency for other currencies
• Investors may also perceive a higher default risk on foreign investments.
© 2018 Cambridge University Press 6-12

Exhibit 6.4 Covered
Interest Parity Deviations
During the Financial
Crisis
These lines are, in all cases, the return on buying a foreign currency, investing and selling forward the returns into dollars, minus the return from a dollar deposit.
In the crisis, the dollar deposit paid a lower interest rate.
The line that says EUR per USD is a typo.
It should say CHF per USD.
© 2018 Cambridge University Press 6-13

6.4 Hedging Transaction Risk in the Money Market
• When Interest Rate Parity holds, there are two ways to hedge a transaction
(either a liability or a receivable)
• Forward contract – use the appropriate forward contract to buy or sell the foreign currency
• Synthetic forward – borrowing / lending the foreign currency and making a transaction in the spot market
© 2018 Cambridge University Press 6-14

6.4 Hedging Transaction Risk in the Money Market
• Zachy’s: Importing wine for €4M, payable in 90 days
• S: $1.10/€; F(t+90): $1.08/€; i($, t+90): 6.00% p.a; i(€, t+90): 13.519% p.a.
• Choice #1: Enter into a forward contract
• Cost in 90 days: € €
• Choice #2: Money Market hedge
4MM × $1.08/ = $4.32MM
• Invest X amount now that becomes what you owe in 90 days
• € €
13.519 90
• €
XX = 4MM/[1 + ( 100 )(360)] = 3,869,229.71
• PV of forward hedge
XX aaaa ssssssaa rraaaarr = 3,869,229.71 × $1.10/€ = $4,256,152.68
6.00 90
• Forward contract is more expensive by $4.96
$4.32MM/ 1 + 100 360 = $4,256,157.64
© 2018 Cambridge University Press 6-15

6.4 Hedging Transaction Risk in the Money Market
• Shetlant: Receive ¥500M in 30 days
• S: ¥179.5/£; F(t+30): ¥180/£; i(£, t+30): 2.70% p.a; i(¥, t+30): 6.01% p.a.
• Choice #1: Sell yen forward
• Earn: £
• Choice #2: Money Market hedge
¥500MM × ¥180/ = $2,777,778
• Borrow PV of ¥500M, and sell at spot
• 500
6.01 30
PPPP = ¥ MM/[1 + (100)(360)] = ¥497,508,313
• FV of forward hedge
£ rrrrrrrrrrrrrr = ¥497,508,313/(¥179.5/£) = £2,771,634
2.70 30
• Forward contract is more expensive by £6,151
£2,771,634 × 1 + 100 360 = £2,777,785
© 2018 Cambridge University Press 6-16

• The term structure of interest rates
• Description of different spot interest rates for various maturities into the future
• Rates derived by:
• Observable direct quotes from banks (short maturities)
• Market prices of coupon paying bonds (longer maturities)
© 2018 Cambridge University Press 6-17

Exhibit 6.5 Yield
Curves for Four
Currencies
© 2018 Cambridge University Press 6-18

• A review of bond pricing
• Price of a 10-year pure discount bond with a face value of $1,000 is $463.19
• What is the spot interest rate for the 10-year maturity expressed in percentage per annum?
• 10
$463.19 × [1 + ii(10)] = $1,000
ii = 8%
© 2018 Cambridge University Press 6-19

Yield to Maturity
• The discount rate that equates the present value of the n coupon payments plus the final principal payment to the current market price
• The yield to maturity is the constant interest rate that solves this equation:
C C C M
B(n,C) = + +  + +
1+ y ( n ) ( ( ))2 ( ( ))n ( ( ))n
1+ y n 1+ y n 1+ y n
• The yield to maturity is y(n)
• B(n,C) is the current price of an n-year bond that pays a coupon C every period.
• M is the value of the bond at maturity – the “face value.”
© 2018 Cambridge University Press 6-20

Yield to Maturity versus Spot Rates
• Yield to maturity
C C C M
B(n,C) = + +  + +
1+ y ( n ) ( ( ))2 ( ( ))n ( ( ))n
1+ y n 1+ y n 1+ y n
• Spot rates
C C C M
B(n,C) = + +  + +
1+ i ( 1 ) ( ( ))2 ( ( ))n ( ( ))n
1+ i 2 1+ i n 1+ i n
© 2018 Cambridge University Press 6-21

• Spot rate
• A 2-year bond with face value of $1,000, an annual coupon of $60, and a market price of $980
• If the 1-year spot rate is 5.5%, the 2-year spot rate is found by solving:
• 2
$980 = ($60/1.055) + ($1060/(1 + ii(2)) )
ii(2) = 7.1574%
• Yield to maturity
• The yield to maturity on this bond is found by solving
• y(2) = 7.11% 2
$980 = ($60/(1 + y(2)) + ($1060/(1 + y(2)) )
© 2018 Cambridge University Press 6-22

• Long-term forward rates and premiums
• Let and denote the spot interest rates for yen and dollar investments with 2year maturities ii(2, ¥) ii(2, $)
• If no arbitrage opportunities exist, then the rate of yen per dollar for the 2-year maturity must be:
• The actual market for 2-ye2ar forward exch2ange is quite small, but the c.i.p. formula would give us the cost
FF(2) = SS × [1 + ii(2,¥)] /[1 + ii(2,$)]
of foreign exchange for a synthetic forward.
• That is, we could take $ dollars today, buy yen, and invest them in a yen account, and have at the end of two years.
2 2
1/[1 + ii(2,$)] SS/[1 + ii(2,$)]
• This has the same costs, in present v2alue terms, of 2committing to spend $1 in two years to buy F(2) yen
SS × [1 + ii(2,¥)] /[1 + ii(2,$)]
© 2018 Cambridge University Press 6-23

The failure of Covered
Interest parity
• Previously, we saw this figure
• Recall that the figure represents (1+i*)(F/S)-(1+i$)
• recall the EUR per USD line should say CHF per USD
• Immediately following the crisis, it seemed profitable to borrow in dollars and invest in foreign currencies.
© 2018 Cambridge University Press 6-24

Du, Tepper, and Verdelhan
• The textbook explains the failure of covered interest rate parity following the crisis in the following way:
• It was not really about default risk. Even when one corrects for the possibility that one of the parties will default on interest rate payments or forward contracts, the deviation from CIP
still holds.
• The textbook concludes that in the immediate aftermath of the crisis, banks and other financial institutions desired liquidity in dollars.
• They were willing to accept lower interest rates even on 30-day deposits in order to have the liquidity
• Du, Teppper and Verdelan find that covered interest parity fails recently, many years after the global financial crisis
© 2018 Cambridge University Press 6-25

## © 2018 Cambridge University Press 6-26

• The returns in this slide are the opposite of the way they are in the Figure from the textbook: negative numbers here mean that the dollar deposits are earning less than the “covered” foreign investment. • Why does this occur even in 2013-2017? The crisis is over. It seems like the need for liquidity has fallen. • Du, Tepper and Verdelhan, in essence, ascribe the problem as a reaction to regulations that were put in place after the crisis. • In order to take advantage of this arbitrage opportunity, banks would need to borrow dollars and then invest them in foreign deposits. • But doing so requires them to increase their liabilities (borrowing dollars or taking in more dollar deposits) and increasing their assets.

• This may put them in danger of violating regulations on their maximum asset/equity, or leverage ratio. • Even though it is a riskless investment opportunity – “free money” – banks will not grab it. • This may be an unintended consequence of the regulation. © 2018 Cambridge University Press 6-27

## © 2018 Cambridge University Press 6-28
