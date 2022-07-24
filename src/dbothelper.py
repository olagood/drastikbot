def is_ascii_cl(x, y):
    """Is x an ascii caseless match for y ?"""
    return x.lower() == y.lower()


def get_day_str(num):
    return {
        0: "Mon",
        1: "Tue",
        2: "Wed",
        3: "Thu",
        4: "Fri",
        5: "Sat",
        6: "Sun"
    }[num]


def get_month_str(num):
    return {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec"
    }[num]
