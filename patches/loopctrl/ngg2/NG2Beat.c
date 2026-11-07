/* TEST043: fixed zone1-1 profile, ported from necroprobe/beat_sync.py.
 * All timestamps belong to one native monotonic clock. Capture start/end
 * midpoints remain unverified estimates, not compositor or touch timestamps.
 * Never construct this model by reusing an HTTP-clock model. Int functions
 * return 1 on success and 0 on refusal; failed outputs are zero initialized.
 * Modes are acquired=1/tracking=2. Absent optional doubles use -1.0.
 */
#include "NG2Core.h"
#include <math.h>
#include <string.h>
#if defined(__clang__)
#pragma clang fp contract(off)
#endif

#define NG2_NS_LIMIT UINT64_C(9223372036854775808)
#define NG2_MIN_PERIOD UINT64_C(515000000)
#define NG2_MAX_PERIOD UINT64_C(530000000)
#define NG2_MIN_SPAN UINT64_C(2000000000)
#define NG2_MAX_SPAN UINT64_C(20000000000)
#define NG2_MAX_SAMPLES 12u
#define NG2_MAX_CANDIDATES 160u
#define NG2_TAU 6.283185307179586

typedef struct { double frequency, intercept, rms, maximum; } NG2Candidate;
typedef struct { double high, low; } NG2Sum;

/* Match Python 3.12 sum's compensated float accumulation. This also avoids a
 * rounding-induced rejection at the generic candidate frequency endpoints. */
static void sum_add(NG2Sum *sum, double value) {
    double combined = sum->high + value;
    if (fabs(sum->high) >= fabs(value)) sum->low += (sum->high - combined) + value;
    else sum->low += (value - combined) + sum->high;
    sum->high = combined;
}

static double sum_value(const NG2Sum *sum) { return sum->high + sum->low; }

static double positive_mod(double value, double divisor) {
    double result = fmod(value, divisor);
    if (result < 0.0) result += divisor;
    return result == 0.0 ? 0.0 : result;
}

/* Python round, including negative half-integers, independent of FE mode. */
static double round_even(double value) {
    double lower = floor(value), fraction = value - lower;
    if (fraction < 0.5) return lower;
    if (fraction > 0.5) return lower + 1.0;
    return fmod(lower, 2.0) == 0.0 ? lower : lower + 1.0;
}

static double distance_cycles(double a, double b) {
    return positive_mod(a - b + 0.5, 1.0) - 0.5;
}

static int circle(const double *values, size_t count, double *out) {
    size_t i;
    NG2Sum real_sum = {0.0, 0.0}, imag_sum = {0.0, 0.0};
    double real, imag;
    for (i = 0; i < count; ++i) {
        sum_add(&real_sum, cos(NG2_TAU * values[i]));
        sum_add(&imag_sum, sin(NG2_TAU * values[i]));
    }
    real = sum_value(&real_sum);
    imag = sum_value(&imag_sum);
    if (hypot(real, imag) < 0.5 * (double)count) return 0;
    *out = positive_mod(atan2(imag, real) / NG2_TAU, 1.0);
    return 1;
}

int ng2_make_sample(double q, double spacing, double center, uint64_t start,
                    uint64_t end, NG2BeatSample *out) {
    if (out == NULL) return 0;
    memset(out, 0, sizeof(*out));
    if (start >= NG2_NS_LIMIT || end >= NG2_NS_LIMIT || end <= start ||
        !isfinite(q) || !isfinite(spacing) || !isfinite(center) ||
        q < 0.0 || q >= 1.0 || spacing < 90.0 || spacing > 120.0 ||
        center < 440.0 || center > 452.0) return 0;
    out->start_ns = start;
    out->end_ns = end;
    out->midpoint_ns = start + (end - start) / 2u;
    out->half_width_ns = (double)(end - start) / 2.0;
    out->q = q;
    out->spacing = spacing;
    out->center = center;
    return 1;
}

static int sample_valid(const NG2BeatSample *sample) {
    NG2BeatSample expected;
    return ng2_make_sample(sample->q, sample->spacing, sample->center,
                           sample->start_ns, sample->end_ns, &expected) &&
        expected.midpoint_ns == sample->midpoint_ns &&
        expected.half_width_ns == sample->half_width_ns;
}

static int samples_valid(const NG2BeatSample *samples, size_t count) {
    size_t i;
    if (samples == NULL) return 0;
    for (i = 0; i < count; ++i)
        if (!sample_valid(&samples[i]) ||
            (i != 0u && samples[i].midpoint_ns <= samples[i - 1u].midpoint_ns)) return 0;
    return 1;
}

static int candidate(const double *times, const double *phases, size_t count,
                     double frequency, NG2Candidate *out) {
    double mean_t = 0.0, variance = 0.0, intercept = 0.0;
    double values[NG2_MAX_SAMPLES], unwrapped[NG2_MAX_SAMPLES];
    double total, mean_q, slope, sum_errors = 0.0, maximum = 0.0;
    size_t i, iteration;
    NG2Sum accumulator = {0.0, 0.0};
    for (i = 0; i < count; ++i) sum_add(&accumulator, times[i]);
    mean_t = sum_value(&accumulator) / (double)count;
    accumulator.high = accumulator.low = 0.0;
    for (i = 0; i < count; ++i) {
        double diff = times[i] - mean_t;
        sum_add(&accumulator, diff * diff);
    }
    variance = sum_value(&accumulator);
    if (variance <= 0.0) return 0;
    for (iteration = 0; iteration < 3u; ++iteration) {
        for (i = 0; i < count; ++i)
            values[i] = positive_mod(phases[i] + frequency * times[i], 1.0);
        if (!circle(values, count, &intercept)) return 0;
        accumulator.high = accumulator.low = 0.0;
        for (i = 0; i < count; ++i) {
            unwrapped[i] = phases[i] + round_even(intercept - frequency * times[i] - phases[i]);
            sum_add(&accumulator, unwrapped[i]);
        }
        mean_q = sum_value(&accumulator) / (double)count;
        accumulator.high = accumulator.low = 0.0;
        for (i = 0; i < count; ++i)
            sum_add(&accumulator, (times[i] - mean_t) * (unwrapped[i] - mean_q));
        total = sum_value(&accumulator);
        slope = total / variance;
        frequency = -slope;
        intercept = mean_q - slope * mean_t;
    }
    if (frequency < 1.25 || frequency > 3.125) return 0;
    accumulator.high = accumulator.low = 0.0;
    for (i = 0; i < count; ++i) {
        double error = distance_cycles(phases[i], intercept - frequency * times[i]);
        double magnitude = fabs(error);
        sum_add(&accumulator, error * error);
        if (magnitude > maximum) maximum = magnitude;
    }
    sum_errors = sum_value(&accumulator);
    out->frequency = frequency;
    out->intercept = positive_mod(intercept, 1.0);
    out->rms = sqrt(sum_errors / (double)count);
    out->maximum = maximum;
    return 1;
}

static uint64_t epoch_for(uint64_t first, uint64_t last, uint64_t period, double intercept) {
    uint64_t epoch = first + (uint64_t)round_even(intercept * (double)period);
    /* Fitting always spans >=2 seconds, so last is after this first epoch. */
    return epoch + ((last - epoch) / period) * period;
}

static void candidate_model(const NG2BeatSample *samples, size_t count,
                             const NG2Candidate *best, NG2BeatModel *out) {
    size_t i;
    out->period_ns = (uint64_t)round_even(1e9 / best->frequency);
    out->first_ns = samples[0].midpoint_ns;
    out->last_ns = samples[count - 1u].midpoint_ns;
    out->epoch_ns = epoch_for(out->first_ns, out->last_ns, out->period_ns, best->intercept);
    out->sample_count = (int32_t)count;
    out->residual = best->rms;
    out->maximum = best->maximum;
    out->alternate = -1.0;
    out->alias_gap = -1.0;
    out->tracking_error = -1.0;
    out->extrapolation_budget = -1.0;
    for (i = 0; i < count; ++i)
        if (samples[i].half_width_ns > out->half_width_max_ns)
            out->half_width_max_ns = samples[i].half_width_ns;
}

int ng2_beat_fit(const NG2BeatSample *samples, size_t count, NG2BeatModel *out) {
    double times[NG2_MAX_SAMPLES], phases[NG2_MAX_SAMPLES], ordered[NG2_MAX_SAMPLES];
    NG2Candidate candidates[NG2_MAX_CANDIDATES], distinct[NG2_MAX_CANDIDATES];
    NG2Candidate inside[NG2_MAX_CANDIDATES], outside[NG2_MAX_CANDIDATES];
    size_t i, j, n = 0u, distinct_n = 0u, inside_n = 0u, outside_n = 0u;
    int low, high, cycles, shift;
    double span, delta, maximum_gap;
    if (out == NULL) return 0;
    memset(out, 0, sizeof(*out));
    if (count < 4u || count > NG2_MAX_SAMPLES || !samples_valid(samples, count)) return 0;
    if (samples[count - 1u].midpoint_ns - samples[0].midpoint_ns < NG2_MIN_SPAN ||
        samples[count - 1u].midpoint_ns - samples[0].midpoint_ns > NG2_MAX_SPAN) return 0;
    for (i = 0; i < count; ++i) {
        times[i] = (double)(samples[i].midpoint_ns - samples[0].midpoint_ns) / 1e9;
        phases[i] = samples[i].q;
        ordered[i] = phases[i];
    }
    for (i = 1u; i < count; ++i) {
        double value = ordered[i];
        for (j = i; j > 0u && ordered[j - 1u] > value; --j) ordered[j] = ordered[j - 1u];
        ordered[j] = value;
    }
    maximum_gap = ordered[0] + 1.0 - ordered[count - 1u];
    for (i = 1u; i < count; ++i)
        if (ordered[i] - ordered[i - 1u] > maximum_gap) maximum_gap = ordered[i] - ordered[i - 1u];
    if (1.0 - maximum_gap < 0.35) return 0;
    span = times[count - 1u];
    delta = phases[0] - phases[count - 1u];
    low = (int)floor(span * 1e9 / 800000000.0 - delta) - 1;
    high = (int)ceil(span * 1e9 / 320000000.0 - delta) + 1;
    for (cycles = low; cycles <= high; ++cycles) {
        for (shift = 0; shift < 2; ++shift) {
            NG2Candidate value;
            double frequency = (delta + (double)cycles + (shift == 0 ? 0.0 : 0.5)) / span;
            if (frequency < 1.25 || frequency > 3.125 ||
                !candidate(times, phases, count, frequency, &value)) continue;
            if (n >= NG2_MAX_CANDIDATES) return 0;
            /* Stable sorting preserves the Python enumeration order for ties. */
            for (j = n; j > 0u && candidates[j - 1u].rms > value.rms; --j)
                candidates[j] = candidates[j - 1u];
            candidates[j] = value;
            ++n;
        }
    }
    for (i = 0; i < n; ++i) {
        for (j = 0; j < distinct_n; ++j)
            if (fabs(candidates[i].frequency - distinct[j].frequency) * span < 0.02) break;
        if (j == distinct_n) distinct[distinct_n++] = candidates[i];
    }
    for (i = 0; i < distinct_n; ++i) {
        uint64_t period = (uint64_t)round_even(1e9 / distinct[i].frequency);
        if (period >= NG2_MIN_PERIOD && period <= NG2_MAX_PERIOD) inside[inside_n++] = distinct[i];
        else outside[outside_n++] = distinct[i];
    }
    if (inside_n == 0u ||
        (outside_n != 0u && outside[0].rms <= inside[0].rms + 1e-9) ||
        inside[0].rms > 0.055 || inside[0].maximum > 0.13 ||
        (inside_n > 1u && inside[1].rms - inside[0].rms < 0.04)) return 0;
    candidate_model(samples, count, &inside[0], out);
    out->mode = 1;
    out->candidate_count = (int32_t)inside_n;
    if (inside_n > 1u) {
        out->alternate = inside[1].rms;
        out->alias_gap = inside[1].rms - inside[0].rms;
    }
    return 1;
}

int ng2_beat_model_valid(const NG2BeatModel *model) {
    if (model == NULL || (model->mode != 1 && model->mode != 2) ||
        model->sample_count < (model->mode == 1 ? 4 : 3) || model->sample_count > 12 ||
        model->period_ns < NG2_MIN_PERIOD || model->period_ns > NG2_MAX_PERIOD ||
        model->first_ns >= NG2_NS_LIMIT || model->last_ns >= NG2_NS_LIMIT ||
        model->last_ns < model->first_ns ||
        model->last_ns - model->first_ns < NG2_MIN_SPAN ||
        model->last_ns - model->first_ns > NG2_MAX_SPAN || model->epoch_ns >= NG2_NS_LIMIT ||
        !isfinite(model->residual) || model->residual < 0.0 || model->residual > 0.055) return 0;
    return 1;
}

static uint64_t phase_remainder(uint64_t epoch, uint64_t time, uint64_t period) {
    if (epoch >= time) return (epoch - time) % period;
    return (period - ((time - epoch) % period)) % period;
}

int ng2_beat_track(const NG2BeatModel *old, const NG2BeatSample *samples,
                   size_t count, NG2BeatModel *out) {
    NG2BeatModel prior;
    NG2Candidate fitted;
    double times[NG2_MAX_SAMPLES], phases[NG2_MAX_SAMPLES];
    double budget, tolerance, error = 0.0, frequency;
    uint64_t old_span, gap, newest;
    size_t i, first = 0u, window_count;
    int retained = 0;
    if (out == NULL) return 0;
    if (old != NULL) prior = *old;
    memset(out, 0, sizeof(*out));
    if (old == NULL || !ng2_beat_model_valid(&prior) || !isfinite(prior.maximum) ||
        prior.maximum < 0.0 || prior.maximum > 0.13 || count < 3u || count > NG2_MAX_SAMPLES ||
        !samples_valid(samples, count)) return 0;
    newest = samples[count - 1u].midpoint_ns;
    old_span = prior.last_ns - prior.first_ns;
    if (newest <= prior.last_ns) return 0;
    gap = newest - prior.last_ns;
    if (gap > old_span) return 0;
    for (i = 0; i < count; ++i) if (samples[i].midpoint_ns == prior.last_ns) retained = 1;
    if (!retained) return 0;
    budget = prior.maximum * (1.0 + 2.0 * (double)gap / (double)old_span);
    if (budget > 0.13) return 0;
    tolerance = fmin(0.13, fmax(0.08, 3.0 * prior.residual));
    for (i = 0; i < count; ++i) {
        if (samples[i].midpoint_ns > prior.last_ns) {
            double expected = (double)phase_remainder(prior.epoch_ns, samples[i].midpoint_ns,
                                                      prior.period_ns) / (double)prior.period_ns;
            error = distance_cycles(samples[i].q, expected);
            if (fabs(error) > tolerance) return 0;
        }
    }
    while (first < count && newest - samples[first].midpoint_ns > NG2_MAX_SPAN) ++first;
    window_count = count - first;
    if (window_count < 3u || newest - samples[first].midpoint_ns < NG2_MIN_SPAN) return 0;
    for (i = 0; i < window_count; ++i) {
        times[i] = (double)(samples[first + i].midpoint_ns - samples[first].midpoint_ns) / 1e9;
        phases[i] = samples[first + i].q;
    }
    frequency = 1e9 / (double)prior.period_ns;
    if (!candidate(times, phases, window_count, frequency, &fitted) || fitted.rms > 0.055 ||
        fitted.maximum > 0.13 || fabs(fitted.frequency - frequency) * ((double)old_span / 1e9) >= 0.5 ||
        round_even(1e9 / fitted.frequency) < (double)NG2_MIN_PERIOD ||
        round_even(1e9 / fitted.frequency) > (double)NG2_MAX_PERIOD) return 0;
    candidate_model(samples + first, window_count, &fitted, out);
    out->mode = 2;
    out->candidate_count = 1;
    out->tracking_error = error;
    out->extrapolation_budget = budget;
    out->gap_ns = gap;
    out->prediction_span_ns = old_span;
    return 1;
}

uint64_t ng2_next_target(const NG2BeatModel *model, uint64_t now, uint64_t lead) {
    uint64_t threshold, remainder, target;
    if (!ng2_beat_model_valid(model) || now >= NG2_NS_LIMIT || lead > UINT64_C(1000000000) ||
        now < model->last_ns || now - model->last_ns > UINT64_C(3000000000)) return 0u;
    threshold = now + lead;
    remainder = phase_remainder(threshold, model->epoch_ns, model->period_ns);
    target = threshold + (model->period_ns - remainder);
    return target < NG2_NS_LIMIT ? target : 0u;
}
