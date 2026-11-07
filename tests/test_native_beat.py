"""TEST043 fixed-profile native beat parity; native midpoints remain unverified.

The ABI uses modes 1/2 for acquired/tracking and -1.0 for Python None in
alternate, alias_gap, tracking_error, and extrapolation_budget. The profile is
fixed by this native module; HTTP-clock models are never imported by production.
"""
import ctypes as C
import json
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from necroprobe import beat_sync
from tests.test_beat_sync import observations, test020_sequences, test022_samples

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "patches/loopctrl/ngg2"
PROFILE = beat_sync.ZONE1_1_PROFILE


class NativeSample(C.Structure):
    _fields_ = [(name, C.c_uint64) for name in ("start_ns", "end_ns", "midpoint_ns")] + [
        (name, C.c_double) for name in ("half_width_ns", "q", "spacing", "center")]


class NativeModel(C.Structure):
    _fields_ = [(name, C.c_uint64) for name in (
        "period_ns", "epoch_ns", "first_ns", "last_ns", "gap_ns", "prediction_span_ns")] + [
        (name, C.c_int32) for name in ("sample_count", "mode", "candidate_count")] + [
        (name, C.c_double) for name in ("residual", "maximum", "alternate", "alias_gap",
                                       "half_width_max_ns", "tracking_error", "extrapolation_budget")]


class NativeCandidate(C.Structure):
    _fields_ = [(name, C.c_double) for name in ("frequency", "intercept", "rms", "maximum")]


def native_sample(sample):
    return NativeSample(*(sample[key] for key in (
        "http_start_ns", "http_end_ns", "midpoint_ns", "http_half_width_ns", "q", "spacing_px", "center_px")))


MODEL_FIELDS = {
    "period_ns": "period_ns", "epoch_ns": "epoch_ns", "first_ns": "first_sample_ns",
    "last_ns": "last_sample_ns", "gap_ns": "gap_ns", "prediction_span_ns": "prediction_span_ns",
    "sample_count": "sample_count", "candidate_count": "candidate_count", "residual": "residual_cycles",
    "maximum": "max_residual_cycles", "alternate": "runner_up_residual_cycles",
    "alias_gap": "alias_gap_cycles", "half_width_max_ns": "http_half_width_max_ns",
    "tracking_error": "tracking_error_cycles", "extrapolation_budget": "extrapolation_budget_cycles",
}


def native_model(model):
    values = {field: (-1.0 if model[key] is None else model[key]) for field, key in MODEL_FIELDS.items()}
    values["mode"] = {"acquired": 1, "tracking": 2}.get(model["mode"], 0)
    return NativeModel(**values)


def sample_at(mid, period=520_000_000, epoch=6_000_000_000_000, noise=0):
    q = ((epoch - mid) % period) / period
    return beat_sync.make_sample({"remaining": (q + noise) % 1, "spacing_px": 104., "center_px": 446.},
                                 mid - 1, mid + 1)


def recorded_samples():
    # Numeric HUD/capture bounds only. These historical HTTP fixtures exercise
    # arithmetic parity and are never loaded into the native runtime model.
    rows = {
        "019": [
            (125945800458000,125945959202000,.8168588335276556,104.19999999999999,445.3),
            (125948201905000,125948343852000,.23269396502147233,104.25,445.25),
            (125949073627000,125949228441000,.5452368766135953,105.,445.25),
            (125950068532000,125950230713000,.6378205669853869,104.,445.25),
            (125950841082000,125950994140000,.16546744438772792,104.25,445.25),
            (125951718836000,125951875846000,.4863295735044895,104.5,445.25),
            (125952693580000,125952838095000,.6522436439084638,104.,445.25),
            (125953478953000,125953642323000,.08931424796841578,104.5,445.25),
            (125954330822000,125954478991000,.453261881866172,104.75,445.16666666666663),
            (125957241759000,125957392901000,.903278050431733,104.25,445.5),
            (125963760450000,125963905148000,.4289133055619059,104.5,445.25)],
        "041": [
            (209134757917000,209134923549000,.8025586259713013,104.25,445.),
            (209136121116000,209136305054000,.17764460800896673,104.375,445.25),
            (209137134544000,209137310118000,.2784671168514601,103.5,445.25),
            (209138233230000,209138407238000,.13477454680061451,104.08333333333331,445.25),
            (209139114575000,209139286583000,.4692031508219258,103.5,445.25),
            (209142007294000,209142161400000,.9024781016349586,104.25,445.25),
            (209145080125000,209145233844000,.016786752254957866,104.25,445.25),
            (209147300045000,209147473123000,.7625897465460014,104.25,445.25),
            (209149757087000,209149916041000,.05476190476190466,105.,445.25),
            (209152491820000,209152639879000,.8345321925891669,104.25,445.25)],
        "042": [
            (211610696345000,211610918671000,.9800158124386286,104.25,445.),
            (211612765433000,211613004357000,.9752204964748985,104.25,445.),
            (211614098772000,211614319718000,.4032455093635623,104.,445.125),
            (211615475006000,211615680535000,.7820513362161562,104.,445.25),
            (211618473474000,211618636652000,.061711335170824985,104.25,445.),
            (211620557727000,211620736637000,.0544876129050513,104.,445.25),
            (211623279511000,211623441252000,.8609121785546803,104.25,445.)],
    }
    result = {"020a": test020_sequences()[0], "020b": test020_sequences()[1],
              "022-used-by-023-profile-tests": test022_samples()}
    for name, values in rows.items():
        result[name] = [beat_sync.make_sample({"remaining": q, "spacing_px": spacing, "center_px": center}, start, end)
                        for start, end, q, spacing, center in values]
    return result


class NativeBeatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="ngg2-beat-")
        output = Path(cls.directory.name) / "beat.so"
        subprocess.run(["cc", "-std=c99", "-pedantic", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-fPIC", "-shared", str(CORE / "NG2Beat.c"), "-lm", "-o", str(output)], check=True)
        cls.native = C.CDLL(str(output))
        cls.native.ng2_make_sample.argtypes = [C.c_double, C.c_double, C.c_double,
                                              C.c_uint64, C.c_uint64, C.POINTER(NativeSample)]
        cls.native.ng2_make_sample.restype = C.c_int
        cls.native.ng2_beat_fit.argtypes = [C.POINTER(NativeSample), C.c_size_t, C.POINTER(NativeModel)]
        cls.native.ng2_beat_fit.restype = C.c_int
        cls.native.ng2_beat_track.argtypes = [C.POINTER(NativeModel), C.POINTER(NativeSample),
                                             C.c_size_t, C.POINTER(NativeModel)]
        cls.native.ng2_beat_track.restype = C.c_int
        cls.native.ng2_beat_model_valid.argtypes = [C.POINTER(NativeModel)]
        cls.native.ng2_beat_model_valid.restype = C.c_int
        cls.native.ng2_next_target.argtypes = [C.POINTER(NativeModel), C.c_uint64, C.c_uint64]
        cls.native.ng2_next_target.restype = C.c_uint64
        wrapper = Path(cls.directory.name) / "helpers.c"
        wrapper.write_text('#include ' + json.dumps(str(CORE / "NG2Beat.c")) + '''
double test_round_even(double value) { return round_even(value); }
double test_positive_mod(double value) { return positive_mod(value, 1.0); }
int test_circle(const double *values, size_t count, double *out) { return circle(values, count, out); }
int test_candidate(const double *times, const double *phases, size_t count,
                   double frequency, NG2Candidate *out) { return candidate(times, phases, count, frequency, out); }
''')
        helper_output = Path(cls.directory.name) / "helpers.so"
        subprocess.run(["cc", "-std=c99", "-pedantic", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-fPIC", "-shared", str(wrapper), "-lm", "-o", str(helper_output)], check=True)
        cls.helpers = C.CDLL(str(helper_output))
        for name in ("test_round_even", "test_positive_mod"):
            getattr(cls.helpers,name).argtypes = [C.c_double]
            getattr(cls.helpers,name).restype = C.c_double
        cls.helpers.test_circle.argtypes = [C.POINTER(C.c_double),C.c_size_t,C.POINTER(C.c_double)]
        cls.helpers.test_circle.restype = C.c_int
        cls.helpers.test_candidate.argtypes = [C.POINTER(C.c_double),C.POINTER(C.c_double),C.c_size_t,
                                                C.c_double,C.POINTER(NativeCandidate)]
        cls.helpers.test_candidate.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def fit(self, samples):
        values = (NativeSample * len(samples))(*(native_sample(sample) for sample in samples))
        model = NativeModel()
        accepted = self.native.ng2_beat_fit(values, len(values), C.byref(model))
        return model if accepted else None

    def track(self, model, samples):
        values = (NativeSample * len(samples))(*(native_sample(sample) for sample in samples))
        old, updated = native_model(model), NativeModel()
        accepted = self.native.ng2_beat_track(C.byref(old), values, len(values), C.byref(updated))
        return updated if accepted else None

    def assert_model(self, expected, actual):
        self.assertEqual(expected is None, actual is None)
        if expected is None:
            return
        self.assertEqual(1 if expected["mode"] == "acquired" else 2, actual.mode)
        for field, key in MODEL_FIELDS.items():
            value = -1.0 if expected[key] is None else expected[key]
            with self.subTest(field=field):
                if isinstance(value, float):
                    self.assertAlmostEqual(value, getattr(actual, field), delta=1e-12)
                else:
                    self.assertEqual(value, getattr(actual, field))
        self.assertEqual(1, self.native.ng2_beat_model_valid(C.byref(actual)))

    def assert_fit(self, samples):
        expected = beat_sync.fit(samples, profile=PROFILE)
        self.assert_model(expected, self.fit(samples))
        return expected

    def test_known_valid_profile_fit_public_entry(self):
        samples = observations(5, noise=True)
        expected = beat_sync.fit(samples, profile=PROFILE)
        self.assertIsNotNone(expected)
        model = self.fit(samples)
        self.assertIsNotNone(model)
        self.assertEqual(expected["period_ns"], model.period_ns)

    def test_recorded_acquisition_and_tracking_all_prefixes(self):
        for name, samples in recorded_samples().items():
            model = None
            for count in range(4, len(samples) + 1):
                values = samples[:count]
                with self.subTest(source=name, count=count):
                    acquired = self.assert_fit(values)
                    if model is not None:
                        tracked = beat_sync.track(model, values)
                        self.assert_model(tracked, self.track(model, values))
                        model = tracked
                    elif acquired is not None:
                        model = acquired

    def test_make_sample_all_feature_and_timestamp_boundaries(self):
        cases = [(0.,90.,440.,0,1), (math.nextafter(1.,0.),120.,452.,2**63-2,2**63-1),
                 (.75,104.,446.,1_000_000_001,1_450_000_002)]
        for field, values in ((0, [-1., math.nextafter(0., -math.inf), 1., math.nan, math.inf, -math.inf]),
                              (1, [math.nextafter(90., -math.inf), math.nextafter(120., math.inf), math.nan]),
                              (2, [math.nextafter(440., -math.inf), math.nextafter(452., math.inf), math.inf])):
            for value in values:
                row = [.25,104.,446.,10,20];row[field] = value;cases.append(tuple(row))
        cases += [(.25,104.,446.,a,b) for a,b in ((1,1),(2,1),(2**63,2**63+1),(0,2**63),
                                                     (2**64-1,0))]
        for q, spacing, center, start, end in cases:
            with self.subTest(q=q, spacing=spacing, center=center, start=start, end=end):
                try:
                    expected = beat_sync.make_sample({"remaining":q,"spacing_px":spacing,"center_px":center},start,end)
                except ValueError:
                    expected = None
                output = NativeSample();C.memset(C.byref(output), 0xA5, C.sizeof(output))
                self.assertEqual(expected is not None,
                    bool(self.native.ng2_make_sample(q,spacing,center,start,end,C.byref(output))))
                if expected is None:
                    self.assertEqual(bytes(C.sizeof(output)), bytes(output))
                else:
                    self.assertEqual(bytes(native_sample(expected)), bytes(output))

    def test_fit_profile_period_span_count_order_coverage_and_corruption(self):
        for period in (320_000_000,514_999_999,515_000_000,520_000_000,530_000_000,530_000_001,800_000_000):
            values = observations(5)
            for sample in values:
                sample["q"] = sample["remaining"] = (.23-(sample["midpoint_ns"]-values[0]["midpoint_ns"])/period)%1
            with self.subTest(period=period):
                self.assert_fit(values)
        values = observations(5)
        for count in (0,1,2,3,4,5,12,13):
            self.assert_fit((values * 3)[:count] if count > 5 else values[:count])
        for span in (1_999_999_999,2_000_000_000,20_000_000_000,20_000_000_001):
            mids = [6_000_000_000_000 + int(span * ratio) for ratio in (0,.19,.57,1)]
            self.assert_fit([sample_at(mid) for mid in mids])
        for samples in (values[::-1], values[:2]+[values[1]]+values[3:], observations(5,uniform=True),
                        [dict(value,q=.25,remaining=.25) for value in values]):
            self.assert_fit(samples)
        for key, value in (("midpoint_ns",values[2]["midpoint_ns"]+1),("http_half_width_ns",0.),
                           ("q",math.nan),("remaining",1.),("spacing_px",89.999),("center_px",452.001),
                           ("http_start_ns",2**63),("http_end_ns",0)):
            samples = [dict(sample) for sample in values];samples[2][key] = value
            # remaining aliases q in C; independently corrupted Python alias has
            # no representation in the ABI and is checked at make_sample instead.
            if key != "remaining":
                self.assert_fit(samples)

    def test_randomized_profile_fit_and_tracking_differential(self):
        rng = random.Random(43023)
        accepted = refused = 0
        for _ in range(180):
            count = rng.randint(4,12);period = rng.randint(505_000_000,540_000_000)
            mids = [6_000_000_000_000]
            for index in range(1,count):mids.append(mids[-1]+rng.randint(350_000_000,1_300_000_000))
            amplitude = rng.choice((0,.003,.025,.06,.13,.25))
            samples = [sample_at(mid,period,noise=rng.uniform(-amplitude,amplitude)) for mid in mids]
            model = self.assert_fit(samples)
            accepted += model is not None;refused += model is None
            if model is not None and count < 12:
                new = sample_at(mids[-1]+rng.randint(400_000_000,2_000_000_000),period,
                                noise=rng.uniform(-amplitude,amplitude))
                self.assert_model(beat_sync.track(model,samples+[new]),self.track(model,samples+[new]))
        self.assertGreater(accepted,10);self.assertGreater(refused,10)

    def test_fit_residual_maximum_coverage_and_alias_threshold_sides(self):
        samples=observations(12)
        times=[(sample["midpoint_ns"]-samples[0]["midpoint_ns"])/1e9 for sample in samples]
        mean=sum(times)/12;variance=sum((time-mean)**2 for time in times)
        for kind,limit in (("rms",.055),("maximum",.13)):
            raw=[(-1)**i for i in range(12)] if kind=="rms" else [int(i==5) for i in range(12)]
            average=sum(raw)/12
            slope=sum((time-mean)*(value-average) for time,value in zip(times,raw))/variance
            errors=[value-average-slope*(time-mean) for time,value in zip(times,raw)]
            denominator=math.sqrt(sum(error*error for error in errors)/12) if kind=="rms" else max(map(abs,errors))
            for delta,accepted in ((-1e-9,True),(1e-9,False)):
                values=[]
                for sample,error in zip(samples,errors):
                    q=(sample["q"]+error*(limit+delta)/denominator)%1
                    values.append(beat_sync.make_sample(dict(sample,remaining=q),
                                                        sample["http_start_ns"],sample["http_end_ns"]))
                with self.subTest(kind=kind,delta=delta):
                    self.assertEqual(accepted,self.assert_fit(values) is not None)
        for edge,accepted in ((.349999999,False),(.35,True),(.350000001,True)):
            values=[]
            for q,cycles in zip((0.,.1,.2,edge),(0,2,4,6)):
                mid=6_000_000_000_000+round((cycles-q)*520_000_000)
                values.append(beat_sync.make_sample({"remaining":q,"spacing_px":104.,"center_px":446.},mid-1,mid+1))
            self.assertEqual(accepted,self.assert_fit(values) is not None)
        # Two distinct branches within the profile straddle the .04 alias gap
        # threshold when one live midpoint moves by just one nanosecond.
        for distance,accepted in ((1_652_384_064,False),(1_652_384_065,True)):
            values=[]
            for seconds in (0.,1.3,20-distance/1e9,20.):
                mid=6_000_000_000_000+round(seconds*1e9)
                q=(.23-seconds/.515)%1
                values.append(beat_sync.make_sample({"remaining":q,"spacing_px":104.,"center_px":446.},mid-1,mid+1))
            model=self.assert_fit(values)
            self.assertEqual(accepted,model is not None)
            if accepted:
                self.assertEqual(2,model["candidate_count"])
                self.assertAlmostEqual(.04,model["alias_gap_cycles"],delta=1e-10)

    def test_model_validation_exact_profile_and_numeric_boundaries(self):
        base = beat_sync.fit(observations(5,noise=True),profile=PROFILE)
        changes = [{}, {"mode":"unknown"}, {"mode":"tracking","sample_count":3},
                   {"sample_count":3},{"sample_count":13},{"period_ns":514_999_999},
                   {"period_ns":515_000_000},{"period_ns":530_000_000},{"period_ns":530_000_001},
                   {"epoch_ns":2**63},{"first_sample_ns":2**63},{"last_sample_ns":2**63},
                   {"first_sample_ns":base["last_sample_ns"]+1}]
        changes += [{"residual_cycles":value} for value in (-1.,0.,.055,math.nextafter(.055,math.inf),math.nan,math.inf)]
        changes += [{"first_sample_ns":base["last_sample_ns"]-span} for span in
                    (1_999_999_999,2_000_000_000,20_000_000_000,20_000_000_001)]
        for change in changes:
            with self.subTest(change=change):
                model = dict(base,**change);actual = native_model(model)
                self.assertEqual(beat_sync._model_valid(model,required_profile=PROFILE),
                                 bool(self.native.ng2_beat_model_valid(C.byref(actual))))

    def test_tracking_budget_gap_window_tolerance_and_invalid_maximum(self):
        samples=observations(9);old=beat_sync.fit(samples,profile=PROFILE)
        last=old["last_sample_ns"];span=last-old["first_sample_ns"]
        def aligned(mid,noise=0):return sample_at(mid,old["period_ns"],old["epoch_ns"],noise)
        for offset in (999_999_999,1_000_000_000):
            values=[aligned(last-1_000_000_000),aligned(last),aligned(last+offset)]
            self.assert_model(beat_sync.track(old,values),self.track(old,values))
        for maximum in (-1.,0.,.13/3,math.nextafter(.13/3,math.inf),.13,math.nextafter(.13,math.inf),math.nan,math.inf):
            model=dict(old,max_residual_cycles=maximum);values=samples+[aligned(last+span)]
            self.assert_model(beat_sync.track(model,values),self.track(model,values))
        for gap in (0,1,span,span+1):
            values=[aligned(last-2_000_000_000),aligned(last),aligned(last+gap)]
            self.assert_model(beat_sync.track(old,values),self.track(old,values))
        for error in (.079999,.08,math.nextafter(.08,math.inf),.081,-.081,.13,.14):
            values=samples+[aligned(last+1_000_000_000,error)]
            self.assert_model(beat_sync.track(old,values),self.track(old,values))
        for values in (samples[-2:],samples,samples[::-1],samples[:-1]+[aligned(last+1_000_000_000)]):
            self.assert_model(beat_sync.track(old,values),self.track(old,values))
        for _ in range(7):
            samples=(samples+[aligned(samples[-1]["midpoint_ns"]+4_000_000_000)])[-12:]
            updated=beat_sync.track(old,samples);self.assert_model(updated,self.track(old,samples))
            self.assertIsNotNone(updated);old=updated
        self.assertLess(old["sample_count"],8)

    def test_next_target_strict_boundary_freshness_lead_negative_modulo_and_overflow(self):
        model=beat_sync.fit(observations(5),profile=PROFILE);last=model["last_sample_ns"]
        for age in (-1,0,1,3_000_000_000,3_000_000_001):
            for lead in (0,150_000_000,1_000_000_000,1_000_000_001,2**63,2**64-1):
                for epoch in (0,model["epoch_ns"],2**63-1):
                    changed=dict(model,epoch_ns=epoch);actual=native_model(changed)
                    self.assertEqual(beat_sync.next_target(changed,last+age,lead) or 0,
                                     self.native.ng2_next_target(C.byref(actual),last+age,lead))
        period=model["period_ns"];boundary=last+((model["epoch_ns"]-last)%period)
        for now in (boundary-1,boundary,boundary+1):
            actual=native_model(model)
            self.assertEqual(beat_sync.next_target(model,now,0),self.native.ng2_next_target(C.byref(actual),now,0))
        model.update(first_sample_ns=2**63-3_000_000_001,last_sample_ns=2**63-1,epoch_ns=2**63-20)
        actual=native_model(model)
        self.assertEqual(0,self.native.ng2_next_target(C.byref(actual),2**63-1,1_000_000_000))
        self.assertIsNone(beat_sync.next_target(model,2**63-1,1_000_000_000))

    def test_nulls_huge_lengths_failure_outputs_and_in_place_tracking(self):
        sample=native_sample(observations(5)[0]);out=NativeModel()
        for count in (0,3,13,2**63,2**64-1):
            C.memset(C.byref(out),0xA5,C.sizeof(out))
            self.assertEqual(0,self.native.ng2_beat_fit(C.byref(sample),count,C.byref(out)))
            self.assertEqual(bytes(C.sizeof(out)),bytes(out))
        self.assertEqual(0,self.native.ng2_beat_fit(None,4,C.byref(out)))
        self.assertEqual(0,self.native.ng2_beat_fit(C.byref(sample),4,None))
        self.assertEqual(0,self.native.ng2_make_sample(.2,104.,446.,0,1,None))
        self.assertEqual(0,self.native.ng2_beat_model_valid(None))
        self.assertEqual(0,self.native.ng2_next_target(None,1,0))
        self.assertEqual(0,self.native.ng2_beat_track(None,None,0,C.byref(out)))
        samples=observations(6);old=beat_sync.fit(samples[:5],profile=PROFILE)
        actual=native_model(old);values=(NativeSample*6)(*(native_sample(sample) for sample in samples))
        self.assertEqual(1,self.native.ng2_beat_track(C.byref(actual),values,6,C.byref(actual)))
        self.assert_model(beat_sync.track(old,samples),actual)

    def test_ties_even_positive_modulo_circle_and_candidate_math(self):
        for value in (-123.5,-3.5,-2.5,-1.5,-.5,0.,.5,1.5,2.5,3.5,123.5,
                      math.nextafter(.5,0.),math.nextafter(.5,math.inf),520_000_000.5):
            self.assertEqual(float(round(value)),self.helpers.test_round_even(value))
        for value in (-100.75,-1.,-.5,-1e-100,0.,.25,1.,100.75):
            self.assertEqual(value%1,self.helpers.test_positive_mod(value))
        for values in ((0.,),(0.,.5),(0.,0.,0.,.5),(.001,.999,.002),(.1,.4,.7)):
            expected=beat_sync._circle(values);actual=C.c_double()
            vector=(C.c_double*len(values))(*values)
            self.assertEqual(expected is not None,bool(self.helpers.test_circle(vector,len(values),C.byref(actual))))
            if expected is not None:self.assertAlmostEqual(expected,actual.value,delta=1e-15)
        for period in (320_000_000,515_000_000,520_000_000,530_000_000,800_000_000):
            for noise in (0.,.04,.13):
                times=[0.,.3,.8,1.7,2.8,4.,5.5]
                phases=[(.23-t/(period/1e9)+(noise if index%2 else -noise))%1 for index,t in enumerate(times)]
                frequency=1e9/period
                expected=beat_sync._candidate(times,phases,frequency);actual=NativeCandidate()
                accepted=self.helpers.test_candidate((C.c_double*7)(*times),(C.c_double*7)(*phases),
                                                       7,frequency,C.byref(actual))
                self.assertEqual(expected is not None,bool(accepted),msg=(period,noise,expected))
                if expected is not None:
                    for field,_ in NativeCandidate._fields_:
                        self.assertAlmostEqual(expected[field],getattr(actual,field),delta=1e-13)

    def test_address_and_undefined_sanitizers_on_public_boundaries(self):
        harness=Path(self.directory.name)/"sanitizers.c"
        rows=[]
        for sample in observations(6):
            rows.append("assert(ng2_make_sample(%r,104.,446.,UINT64_C(%d),UINT64_C(%d),&samples[%d]));" %
                        (sample["q"],sample["http_start_ns"],sample["http_end_ns"],len(rows)))
        harness.write_text('#include <assert.h>\n#include '+json.dumps(str(CORE/"NG2Beat.c"))+'''
int main(void) {
    NG2BeatSample samples[6];
    NG2BeatModel model, tracked;
'''+'\n'.join(rows)+'''
    assert(ng2_beat_fit(samples, 5u, &model));
    assert(ng2_beat_track(&model, samples, 6u, &tracked));
    assert(ng2_beat_track(&model, samples, 6u, &model));
    assert(ng2_next_target(&tracked, tracked.last_ns, UINT64_C(150000000)) > tracked.last_ns);
    assert(!ng2_beat_fit(samples, SIZE_MAX, &model));
    assert(!ng2_beat_fit(NULL, 4u, &model));
    assert(!ng2_beat_fit(samples, 5u, NULL));
    assert(!ng2_beat_track(NULL, samples, 6u, &model));
    assert(!ng2_beat_track(&tracked, NULL, 3u, &model));
    assert(!ng2_beat_track(&tracked, samples, SIZE_MAX, &model));
    assert(!ng2_beat_model_valid(NULL));
    assert(!ng2_next_target(NULL, 1u, 0u));
    assert(!ng2_make_sample(.2, 104., 446., 0u, NG2_NS_LIMIT, &samples[0]));
    assert(!ng2_make_sample(NAN, 104., 446., 0u, 1u, &samples[0]));
    samples[0].q = INFINITY;
    assert(!ng2_beat_fit(samples, 5u, &model));
    tracked.first_ns = NG2_NS_LIMIT - UINT64_C(3000000001);
    tracked.last_ns = NG2_NS_LIMIT - 1u;
    tracked.epoch_ns = NG2_NS_LIMIT - 20u;
    assert(!ng2_next_target(&tracked, NG2_NS_LIMIT - 1u, UINT64_C(1000000000)));
    return 0;
}
''')
        executable=Path(self.directory.name)/"sanitizers"
        subprocess.run(["cc","-std=c99","-pedantic","-O1","-g","-Wall","-Wextra","-Werror",
                        "-fsanitize=address,undefined","-fno-omit-frame-pointer",str(harness),"-lm","-o",str(executable)],
                       check=True,capture_output=True,text=True)
        # The managed runner uses ptrace, which LeakSanitizer cannot inspect.
        # ASan address checks and UBSan stay enabled; this core never allocates.
        result=subprocess.run([str(executable)],capture_output=True,text=True,
                              env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0"))
        self.assertEqual(0,result.returncode,result.stderr)


if __name__ == "__main__":
    unittest.main()
