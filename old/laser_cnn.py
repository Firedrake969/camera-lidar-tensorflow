import sys
import numpy as np
import random
import math
import json

from databatch import batch

import tensorflow as tf

training_iters = 10000
batch_size = 10
display_step = 1

n_input = 271
n_output = 1
dropout = 0.75


x = tf.placeholder(tf.float32, [None, n_input])
y = tf.placeholder(tf.float32, [None, n_output])
keep_prob = tf.placeholder(tf.float32) #dropout (keep probability)


# Create some wrappers for simplicity
def conv1d(x, W, b, stride=1):
    # Conv2D wrapper, with bias and relu activation
    x = tf.nn.conv1d(x, W, stride=stride, padding='SAME')
    x = tf.nn.bias_add(x, b)
    return tf.nn.relu(x)

# Create model
def conv_net(x, weights, biases, dropout):
    # Reshape input picture
    out = tf.reshape(x, shape=[-1, 271, 1])

    # Convolution Layer
    out = conv1d(out, weights['wc1'], biases['bc1'])
    print out.get_shape()
    out = conv1d(out, weights['wc2'], biases['bc2'])
    # Max Pooling (down-sampling)
    # conv1 = maxpool2d(conv1, k=2)
    # print conv1.get_shape()

    out = tf.reshape(out, [-1, weights['fc1'].get_shape().as_list()[0]])
    out = tf.add(tf.matmul(out, weights['fc1']), biases['fc1'])
    out = tf.nn.relu(out)
    # Apply Dropout
    # fc1 = tf.nn.dropout(fc1, dropout)

    out = tf.add(tf.matmul(out, weights['fc2']), biases['fc2'])
    out = tf.nn.relu(out)

    # Output, class prediction
    out = tf.add(tf.matmul(out, weights['out']), biases['out'])
    return out

# Store layers weight & bias
conv_size = 5
l1_size = 24
l2_size = 24
full_size_1 = 32
full_size_2 = 16
weights = {
    # 1 input, 32 outputs
    'wc1': tf.Variable(tf.random_normal([conv_size, 1, l1_size])),
    'wc2': tf.Variable(tf.random_normal([conv_size, l1_size, l2_size])),
    'fc1': tf.Variable(tf.random_normal([271 * l2_size, full_size_1])),
    'fc2': tf.Variable(tf.random_normal([full_size_1, full_size_2])),
    # full_size inputs, 1 output
    'out': tf.Variable(tf.random_normal([full_size_2, n_output]))
}

biases = {
    'bc1': tf.Variable(tf.random_normal([l1_size])),
    'bc2': tf.Variable(tf.random_normal([l2_size])),
    'fc1': tf.Variable(tf.random_normal([full_size_1])),
    'fc2': tf.Variable(tf.random_normal([full_size_2])),
    'out': tf.Variable(tf.random_normal([n_output]))
}


print 'constructing model...'
pred = conv_net(x, weights, biases, keep_prob)
print pred.get_shape()
print 'model constructed'

cost = tf.reduce_mean(tf.squared_difference(pred, y))
learning_rate = tf.placeholder(tf.float32, shape=[])
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)
print 'optimizer created'

init = tf.global_variables_initializer()
print 'init created'

max_rate = 1.0
min_rate = 0.0
def get_learning_rate(last_loss):
    return 0.001
    if last_loss is None:
        return 1.0
    rate = min(last_loss/10000.0, max_rate)
    return max(rate, min_rate)

last_loss = None
saver = tf.train.Saver()
save_step = 10
past_losses = []
loss_history = 5
lowest_loss = 1000.0
lowest_iter = 0
with tf.Session() as sess:
    print 'initializing'
    sess.run(init)
    print 'session launched'
    for step in range(training_iters):
        features, targets = batch(batch_size, mode='laser', laser_cdf=False)
        sess.run(optimizer, feed_dict={x: features, y: targets,
                                       keep_prob: 1.0,
                                       learning_rate: get_learning_rate(last_loss)})
        if step % display_step == 0:
            loss = sess.run(cost, feed_dict={x: features,
                                             y: targets,
                                             keep_prob: 1.})
            last_loss = loss
            lowest_loss = min(lowest_loss, loss)
            if lowest_loss == loss:
                lowest_iter = step
            print("Iter {}, Minibatch Loss={}".format(step, np.sqrt(loss/100**2)))
            # predictions = sess.run(pred, feed_dict={x: features})
            # print [float(p[0])/100.0 for p in predictions]
        if step % save_step == 0:
            saver.save(sess, 'models/laser_cnn.ckpt')
    print 'creating whole prediction set...'
    features, targets = batch(1000000, mode='laser', laser_cdf=False)
    predictions = sess.run(pred, feed_dict={x: features})
    targets = [t[0]/(100) for t in targets]
    predictions = [float(p[0])/100.0 for p in predictions]
    combined = zip(targets, predictions)
    with open('laser_cnn_pred.json', 'wb') as f:
        json.dump(combined, f, indent=4)

print lowest_iter, lowest_loss