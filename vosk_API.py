#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import pyaudio
import json
from typing import (
    Dict,
    IO,
    List,
    Optional,
    Callable,
    Set,
    Tuple,
)

def from_words_to_digits_setup_once() -> Tuple[Dict[str, Tuple[int, int, str, bool]], Set[str], Set[str], Set[str]]:

    number_words = {}
    # A set of words that can be used to start numeric expressions.
    valid_digit_words = set()

    # Singles.
    units = (
        (("zero", ""), ("zeroes", "'s"), ("zeroth", "th")),
        (("one", ""), ("ones", "'s"), ("first", "st")),
        (("two", ""), ("twos", "'s"), ("second", "nd")),
        (("three", ""), ("threes", "'s"), ("third", "rd")),
        (("four", ""), ("fours", "'s"), ("fourth", "th")),
        (("five", ""), ("fives", "'s"), ("fifth", "th")),
        (("six", ""), ("sixes", "'s"), ("sixth", "th")),
        (("seven", ""), ("sevens", "'s"), ("seventh", "th")),
        (("eight", ""), ("eights", "'s"), ("eighth", "th")),
        (("nine", ""), ("nines", "'s"), ("ninth", "th")),
        (("ten", ""), ("tens", "'s"), ("tenth", "th")),
        (("eleven", ""), ("elevens", "'s"), ("eleventh", "th")),
        (("twelve", ""), ("twelves", "'s"), ("twelfth", "th")),
        (("thirteen", ""), ("thirteens", "'s"), ("thirteenth", "th")),
        (("fourteen", ""), ("fourteens", "'s"), ("fourteenth", "th")),
        (("fifteen", ""), ("fifteens", "'s"), ("fifteenth", "th")),
        (("sixteen", ""), ("sixteens", "'s"), ("sixteenth", "th")),
        (("seventeen", ""), ("seventeens", "'s"), ("seventeenth", "th")),
        (("eighteen", ""), ("eighteens", "'s"), ("eighteenth", "th")),
        (("nineteen", ""), ("nineteens", "'s"), ("nineteenth", "th")),
    )

    # Tens.
    units_tens = (
        (("", ""), ("", ""), ("", "")),
        (("", ""), ("", ""), ("", "")),
        (("twenty", ""), ("twenties", "'s"), ("twentieth", "th")),
        (("thirty", ""), ("thirties", "'s"), ("thirtieth", "th")),
        (("forty", ""), ("forties", "'s"), ("fortieth", "th")),
        (("fifty", ""), ("fifties", "'s"), ("fiftieth", "th")),
        (("sixty", ""), ("sixties", "'s"), ("sixtieth", "th")),
        (("seventy", ""), ("seventies", "'s"), ("seventieth", "th")),
        (("eighty", ""), ("eighties", "'s"), ("eightieth", "th")),
        (("ninety", ""), ("nineties", "'s"), ("ninetieth", "th")),
    )

    # Larger scales.
    scales = (
        ((("hundred", ""), ("hundreds", "s"), ("hundredth", "th")), 2),
        ((("thousand", ""), ("thousands", "s"), ("thousandth", "th")), 3),
        ((("million", ""), ("millions", "s"), ("millionth", "th")), 6),
        ((("billion", ""), ("billions", "s"), ("billionth", "th")), 9),
        ((("trillion", ""), ("trillions", "s"), ("trillionth", "th")), 12),
        ((("quadrillion", ""), ("quadrillions", "s"), ("quadrillionth", "th")), 15),
        ((("quintillion", ""), ("quintillions", "s"), ("quintillionth", "th")), 18),
    )

    # Divisors (not final).
    number_words["and"] = (1, 0, "", False)

    # Perform our loops and start the swap.
    for idx, word_pairs in enumerate(units):
        for word, suffix in word_pairs:
            number_words[word] = (1, idx, suffix, True)
    for idx, word_pairs in enumerate(units_tens):
        for word, suffix in word_pairs:
            number_words[word] = (1, idx * 10, suffix, True)
    for idx, (word_pairs, power) in enumerate(scales):
        for word, suffix in word_pairs:
            number_words[word] = (10 ** power, 0, suffix, True)

    # Needed for 'imply_single_unit'
    valid_scale_words = set()
    for idx, (word_pairs, power) in enumerate(scales):
        for word, suffix in word_pairs:
            valid_scale_words.add(word)

    valid_unit_words = set()
    for units_iter in (units, units_tens):
        for idx, word_pairs in enumerate(units_iter):
            for word, suffix in word_pairs:
                valid_unit_words.add(word)

    valid_digit_words.update(number_words.keys())
    valid_digit_words.remove("and")
    valid_digit_words.remove("")
    return (
        number_words,
        valid_digit_words,
        valid_unit_words,
        valid_scale_words,
    )


# Originally based on: https://ao.gl/how-to-convert-numeric-words-into-numbers-using-python/
# A module like class can't be instanced.
class from_words_to_digits:

    (
        _number_words,
        valid_digit_words,
        valid_unit_words,
        valid_scale_words,
    ) = from_words_to_digits_setup_once()

    def _parse_number_as_series_of_units(
        word_list: List[str],
        word_index: int,
    ) -> Tuple[int, str, int]:
        """
        Convert a series of unit numbers into a single int.
        `one two three` -> `123`.
        """
        number_words = from_words_to_digits._number_words

        # First detect a series of numbers, e.g:
        # two four six eight
        # Should be 2468 not the result of (2+4+6+8).
        word_index_init = word_index
        unit_numbers = []
        while word_index < len(word_list):
            word_data = number_words.get(word_list[word_index])
            if word_data is None:
                break

            scale, increment, suffix, is_final = word_data
            # Never accumulate numbers with "and" this can stay as a literal.
            if not is_final:
                break
            if suffix == "" and scale == 1 and increment < 10:
                unit_numbers.append(increment)
                word_index += 1
            else:
                break

        if len(unit_numbers) > 1:
            return int("".join([str(n) for n in unit_numbers])), "", word_index

        return 0, "", word_index_init

    def parse_number(
        word_list: List[str],
        word_index: int,
        imply_single_unit: bool = False,
    ) -> Tuple[int, str, int]:
        number_words = from_words_to_digits._number_words
        valid_scale_words = from_words_to_digits.valid_scale_words
        valid_unit_words = from_words_to_digits.valid_unit_words

        # Check if this is a series of unit values, in this case it makes most sense to put the number in a series
        # (think reciting a phone number).
        ret = from_words_to_digits._parse_number_as_series_of_units(word_list, word_index)
        if ret[2] != word_index:
            return ret
        del ret

        if imply_single_unit:
            only_scale = True

        # Primary loop.
        current = result = 0
        suffix = ""

        # This prevents "one and" from being evaluated.
        is_final = False
        word_index_final = -1
        result_final = (0, "", word_index)

        # Loop while splitting to break into individual words.
        while word_index < len(word_list):
            word_data = number_words.get(word_list[word_index])
            if word_data is None:
                # raise Exception('Illegal word: ' + word)
                break

            # Use the index by the multiplier.
            scale, increment, suffix, is_final = word_data

            # This prevents "three and two" from resolving to "5".
            # which we never want, unlike "three hundred and two" which resolves to "302"
            if not is_final:
                if word_index_final != -1:
                    if word_list[word_index_final - 1] in valid_unit_words:
                        break

            if imply_single_unit:
                if only_scale:
                    if word_list[word_index] not in valid_scale_words:
                        only_scale = False

                    if only_scale and current == 0 and result == 0:
                        current = 1 * scale
                        word_index += 1
                        break

            current = (current * scale) + increment

            # If larger than 100 then push for a round 2.
            if scale > 100:
                result += current
                current = 0

            word_index += 1

            if is_final:
                result_final = (result + current, suffix, word_index)
                word_index_final = word_index

            # Once there is a suffix, don't attempt to parse extra numbers.
            if suffix:
                break

        if not is_final:
            # Use the last final result as the output (this resolves problems with a trailing 'and')
            return result_final

        # Return the result plus the current.
        return result + current, suffix, word_index

    @staticmethod
    def parse_numbers_in_word_list(
        word_list: List[str],
        numbers_use_separator: bool = False,
    ) -> None:
        i = 0
        i_number_prev = -1
        while i < len(word_list):
            if word_list[i] in from_words_to_digits.valid_digit_words:
                number, suffix, i_next = from_words_to_digits.parse_number(word_list, i, imply_single_unit=True)
                if i != i_next:
                    word_list[i:i_next] = [("{:,d}".format(number) if numbers_use_separator else str(number)) + suffix]

                    if (i_number_prev != -1) and (i_number_prev + 1 != i):
                        words_between = tuple(word_list[i_number_prev + 1 : i])
                        found = True
                        # While more could be added here, for now this is enough.
                        if words_between == ("point",):
                            word_list[i_number_prev : i + 1] = [word_list[i_number_prev] + "." + word_list[i]]
                        elif words_between == ("minus",):
                            word_list[i_number_prev : i + 1] = [word_list[i_number_prev] + " - " + word_list[i]]
                        elif words_between == ("plus",):
                            word_list[i_number_prev : i + 1] = [word_list[i_number_prev] + " + " + word_list[i]]
                        elif words_between == ("divided", "by"):
                            word_list[i_number_prev : i + 1] = [word_list[i_number_prev] + " / " + word_list[i]]
                        elif words_between in {("multiplied", "by"), ("times",)}:
                            word_list[i_number_prev : i + 1] = [word_list[i_number_prev] + " * " + word_list[i]]
                        elif words_between == ("modulo",):
                            word_list[i_number_prev : i + 1] = [word_list[i_number_prev] + " % " + word_list[i]]
                        else:
                            found = False

                        if found:
                            i = i_number_prev

                    i_number_prev = i
                    i -= 1
            i += 1


# -----------------------------------------------------------------------------
# Process Text
#

def process_text(
    text: str,
    numbers_as_digits: bool = False,
    numbers_use_separator: bool = False):
    """
    Basic post processing on text.
    Mainly to capitalize words however other kinds of replacements may be supported.
    """

    # Make absolutely sure we never add new lines in text that is typed in.
    # As this will press the return key when using automated key input.
    text = text.replace("\n", " ")
    words = text.split(" ")

    # Fist parse numbers.
    if numbers_as_digits:
        from_words_to_digits.parse_numbers_in_word_list(
            words,
            numbers_use_separator=numbers_use_separator,
        )

    return " ".join(words)

def vosk_detect():
    try:
        SetLogLevel(-1)
        model = Model("model")
        rec = KaldiRecognizer(model, 16000)
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True,  frames_per_buffer=4000)
        stream.start_stream()
        print('Say something')
        while True:
            data = stream.read(4000, False)
            if len(data) == 0:
                continue
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result())['text']
                if text:
                    result = process_text(text,numbers_as_digits=True)
                    print(result)
                    return result
                    break
    except KeyboardInterrupt:
        pass
