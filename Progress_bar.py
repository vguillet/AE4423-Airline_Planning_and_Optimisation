from time import time as current_time
class Progress_bar():
    def __init__(self,max_len,name='',bar_length = 40):
        if name != '':
            print(f'{name}...')
        self.index = 0
        self.max_len = max_len
        self.status = 0

        self.not_done = True
        self.bar_length = bar_length

        self.t_start = current_time()
        self.average_speed = 1 / 60
        # self.print_bar()

    def update(self,index = False):
        if not index:
            self.index +=1
        else:
            self.index = index

        self.status = self.index/(self.max_len-1)

        dt = current_time() - self.t_start

        if dt != 0:
            self.average_speed = self.status / dt

        if self.not_done:
            self.print_bar()

    def print_bar(self):
        bar_list = []
        last_index = 0
        for i in range(self.bar_length):
            if i/self.bar_length < self.status:
                bar_list.append('=')
                last_index = i
            else:
                bar_list.append(' ')

        if last_index != self.bar_length-1:
            bar_list[last_index] = '>'
        bar = ''.join(bar_list)

        time_to_go = (1-self.status)/self.average_speed

        percentage = str(round(self.status*100))
        while len(percentage) < 3:
            percentage=' '+percentage

        print(f'\r[{bar}] {percentage}%  {self.time_to_string(time_to_go)} remaining',end = '')

        if self.status == 1:
            self.done()

    def time_to_string(self,time):
        minutes = 0
        while time > (minutes+1)*60:
            minutes += 1
        seconds = str(round(time - minutes*60))
        minutes = str(minutes)

        if len(minutes) < 2:
            minutes = ' '+minutes

        if len(seconds) < 2:
            seconds = '0'+seconds

        time_string = f'{minutes}:{seconds}'

        return time_string

    def done(self):
        progress_time = current_time()-self.t_start
        if self.not_done:
            print(f' | total progress time: {self.time_to_string(progress_time)}')
        self.not_done = False
