# Frozen normalized ciphertext-score transfer

This is a finite-distribution/statistical-dependence experiment in the toy ML-KEM model. It is not evidence of a production ML-KEM vulnerability.

Frozen E0 artifact SHA-256: `1d279c146e2eee4f3adceb01b22132025d8e21c2d66543ae65797c52496a6228`.

## A. Does one frozen normalized score retain positive amplification from n=2 to n=4?

**Answer: yes at the point-estimate level, but the effect is much weaker than at E0.** For q=19 every predeclared n=4 interval excludes zero; for q=29 only s=2 and s=4 do, while the rarer-selection intervals include zero.

- **e0:** joint-score gain bits s=2: 0.96907666105935597, s=4: 0.96570467988837383, s=6: 1.2669541369157968, s=8: 1.4211514134829821, s=10: 1.4211514134829821.
- **e1a:** joint-score gain bits s=2: 0.44012372510251752, s=4: 0.05857770922923549, s=6: -0.060928316668037358, s=8: 0.18575351803039403, s=10: 0.73782032481470405.
- **n4q29d43:** joint-score gain bits s=2: 0.22199124192413025, s=4: 0.21327985827978097, s=6: 0.22853425787292084, s=8: 0.20451898129689849, s=10: 0.11957678422382867.
- **n4q19d43:** joint-score gain bits s=2: 0.13767879815813916, s=4: 0.17179799837079102, s=6: 0.22763441584984467, s=8: 0.25003627576822485, s=10: 0.3076672674677754.

A positive gain means the unchanged E0 score retains failure amplification; n=4 intervals reflect only sampled-key uncertainty.

## B. Does amplification remain when the numerical threshold is frozen?

**Answer: partially, and not robustly at the rarest thresholds.** q=19 has positive point estimates at every E0 threshold, but only s=2 and s=4 exclude zero. q=29 is positive through s=6 at the point-estimate level and becomes strongly negative at s=8 and s=10. E1a has nonzero selected mass only at s=2.

- **e1a:** s=2: p=0.0097201339425802887, G=0.069109480696067052, s=4: p=0, G=NA, s=6: p=0, G=NA, s=8: p=0, G=NA, s=10: p=0, G=NA.
- **n4q29d43:** s=2: p=0.38337624692940153, G=0.21342981264169136, s=4: p=0.032729973696405068, G=0.21068245353767406, s=6: p=0.0020855532493442297, G=0.23945602128685448, s=8: p=4.3107196688652039e-05, G=-2.2131019617210237, s=10: p=4.3107196688652039e-05, G=-2.2131019617210237.
- **n4q19d43:** s=2: p=0.13195105496561155, G=0.1613195529250073, s=4: p=0.0017558342660777271, G=0.27964664614005397, s=6: p=4.1229388443753123e-05, G=0.26797926351487006, s=8: p=5.9214653447270393e-07, G=0.13720255311910393, s=10: p=5.9214653447270393e-07, G=0.13720255311910393.

Thresholds above are copied bit-for-bit from E0. `NA` means the numerical predicate selected no evaluation mass.

## C. Is the joint u-v score materially stronger than the marginal score?

**Answer: not after transfer to n=4.** The two n=4 AUCs slightly favor the marginal score, and every n=4 delta-G interval includes zero. Joint structure is stronger in the rare E0 tail, but that advantage does not transfer consistently.

- **e0:** AUC joint=0.713185, marginal=0.712216; delta-G s=2: -0.027408762855995139, s=4: 0.17909329231628734, s=6: 0.80862489844719243, s=8: 2.3985885248421965, s=10: 2.3985885248421965.
- **e1a:** AUC joint=0.613697, marginal=0.599418; delta-G s=2: -0.095212871868090132, s=4: -0.49348900664453316, s=6: -0.34868498168413353, s=8: -0.59672264352260163, s=10: 0.98066075746178616.
- **n4q29d43:** AUC joint=0.553744, marginal=0.556444; delta-G s=2: -0.0038124724808782096, s=4: -0.058306809111452085, s=6: -0.021013746114223603, s=8: 0.041577712690996749, s=10: 0.21039354120992615.
- **n4q19d43:** AUC joint=0.531931, marginal=0.533284; delta-G s=2: -0.0036005873870952609, s=4: 0.0095816470443823576, s=6: 0.040619662206995144, s=8: 0.015112293188939141, s=10: 0.080918301491057026.

Positive delta-G favors aligned joint u-v structure at that operating point; the AUC comparison summarizes all thresholds.

## D. Does high public score shift executions toward the decoding boundary?

**Answer: yes systematically in both n=4 mixtures, but not monotonically in E1a.** From the lowest to highest score quintile, mean margin falls and failure probability rises for both n=4 points. E0 has the same overall trend; E1a has substantial non-monotonicity across its middle quintiles.

- **e0:** Q1: E[M]=3.8103303380937992, P[F]=0.014909008936542933, Q2: E[M]=3.8264892037323155, P[F]=0.042063674178788306, Q3: E[M]=2.8785895192148208, P[F]=0.073397730162474417, Q4: E[M]=2.6759476227305381, P[F]=0.11460487352045245, Q5: E[M]=2.1835466582585403, P[F]=0.16914450485359445.
- **e1a:** Q1: E[M]=4.6230747995256145, P[F]=0.010025967523733305, Q2: E[M]=3.2248578249153046, P[F]=0.055864306479655776, Q3: E[M]=4.0023335550459596, P[F]=0.03058696397824932, Q4: E[M]=3.2307577762527888, P[F]=0.05716361264871421, Q5: E[M]=3.2003353569479573, P[F]=0.055631437958964629.
- **n4q29d43:** Q1: E[M]=4.7863471540228915, P[F]=0.0035406406370931372, Q2: E[M]=4.5265117056141655, P[F]=0.005463224690692544, Q3: E[M]=4.441925309093504, P[F]=0.0060490061660049927, Q4: E[M]=4.4151266138242677, P[F]=0.0064890920523882735, Q5: E[M]=4.403851673914037, P[F]=0.0065049019826448904.
- **n4q19d43:** Q1: E[M]=2.6993014498003558, P[F]=0.039389447277512334, Q2: E[M]=2.4864766271364811, P[F]=0.050457847834386581, Q3: E[M]=2.4274170664041259, P[F]=0.053095905207195662, Q4: E[M]=2.4046522245845492, P[F]=0.053810997007390539, Q5: E[M]=2.3520632976225544, P[F]=0.055862260763786913.

The conditional-CDF figure shows whether this change is a distribution-wide leftward shift rather than only a change in the failure tail.

## Uncertainty and scope

E0 and E1a probabilities are exact. Each n=4 point is the empirical mixture of 128 sampled outer keys with exact inner encapsulation enumeration. Its 95% intervals use the predeclared paired cluster bootstrap and are not population D-infinity bounds.

The optional n=8 extension was not run: the repository's predeclared E5 n=8 point has a certificate of empty failure support, and choosing a new nonzero-failure n=8 point after viewing these results would violate the frozen-transfer protocol.
