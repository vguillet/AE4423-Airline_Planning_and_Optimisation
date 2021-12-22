from time import time as current_time
class Progress_bar():
    def __init__(self,max_len,name='',bar_length = 40):
        if name != '':
            print(f'----------------> \033[34m{name}\033[0m ...')
        self.index = 0
        self.max_len = max_len
        self.status = 0

        self.not_done = True
        self.bar_length = bar_length

        self.t_start = current_time()
        self.average_speed = 1 / 60
        self.acc = 0
        # self.print_bar()

    def update(self,index = -1):
        if index == -1:
            self.index +=1
        else:
            self.index = index

        self.status = self.index/(self.max_len-1)

        dt = current_time() - self.t_start

        if dt != 0:
            self.acc = self.average_speed - self.status / dt
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

        if self.acc > 0:
            acc = "\033[31m^\033[0m"
        elif self.acc < 0:
            acc = "\033[32mv\033[0m"
        else:
            acc = "-"

        progress_time = self.time_to_string( current_time()-self.t_start + time_to_go)

        end = ''
        word = 'expected'
        if self.status == 1:
            self.not_done = False
            end = '\n'
            word = 'total'
            acc = ''

        print(f'\r[{bar}] {percentage}%  {self.time_to_string(time_to_go)} remaining | {word} process time: {progress_time} {acc}',end = end)

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

