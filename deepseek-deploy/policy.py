"""DeepSeek App's user-required timing and mode contract."""
def interval_range(configured):
 # Archived batches remain readable, but every future send obeys the new floor.
 if type(configured) is not int or not 600<=configured<=1800:raise ValueError('DeepSeek发送间隔须在20–30分钟之间')
 minimum=max(1200,configured)
 return minimum,min(1800,minimum+600)
