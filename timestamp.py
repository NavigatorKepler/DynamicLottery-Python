from time import strftime, localtime

def time_stamp(*args):              # 将时间戳转换为日期
    timestamp = args[0] if args else None
    time = str(strftime('%Y', localtime(timestamp)) + '年' +
               strftime('%m', localtime(timestamp)) + '月' +
               strftime('%d', localtime(timestamp)) + '日' +
               strftime('%H', localtime(timestamp)) + '时' +
               strftime('%M', localtime(timestamp)) + '分' +
               strftime('%S', localtime(timestamp)) + '秒')
    return time