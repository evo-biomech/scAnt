# multi-threading version of focus stacking script

import queue
import threading
import time
import sys
import os
import numpy as np

exitFlag = 0


class myThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        process_data(self.name, self.q)
        print("Exiting " + self.name)


def process_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            data = q.get()
            queueLock.release()
            print("%s processing %s" % (threadName, data))
        else:
            queueLock.release()


def getThreads():
    """ Returns the number of available threads on a posix/win based system """
    if sys.platform == 'win32':
        return int(os.environ['NUMBER_OF_PROCESSORS'])
    else:
        return int(os.popen('grep -c cores /proc/cpuinfo').read())


def createThreadList(num_threads):
    threadNames = []
    for t in range(num_threads):
        threadNames.append("Thread_" + str(t))

    return threadNames


num_virtual_cores = getThreads()
print("Found", num_virtual_cores, "(virtual) cores...")

begin = time.time()

threadList = createThreadList(num_virtual_cores)
nameList = np.arange(0,
                     1000000)  # ["Zero","One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
queueLock = threading.Lock()
workQueue = queue.Queue(1000000)
threads = []
threadID = 1

# Create new threads
for tName in threadList:
    thread = myThread(threadID, tName, workQueue)
    thread.start()
    threads.append(thread)
    threadID += 1

# Fill the queue
queueLock.acquire()
for word in nameList:
    workQueue.put(word)
queueLock.release()

# Wait for queue to empty
while not workQueue.empty():
    print("More work to do!")
    # pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
    t.join()
print("Exiting Main Thread")

end = time.time()

print("This took", np.round(end - begin, 4), "seconds, using", num_virtual_cores, "threads")
