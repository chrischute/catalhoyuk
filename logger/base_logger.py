import os
import torch.nn.functional as F
import util

from constants import CATAL_MEAN, CATAL_STD
from datetime import datetime
from tensorboardX import SummaryWriter


class BaseLogger(object):
    def __init__(self, args, dataset_len):

        def round_down(x, m):
            """Round x down to a multiple of m."""
            return int(m * round(float(x) / m))

        self.args = args
        self.batch_size = args.batch_size
        self.dataset_len = dataset_len
        self.device = args.device
        self.num_visuals = args.num_visuals
        self.save_dir = args.save_dir if args.is_training else args.results_dir
        self.log_path = os.path.join(self.save_dir, '{}.log'.format(args.name))
        log_dir = os.path.join('logs', args.name + '_' + datetime.now().strftime('%b%d_%H%M'))
        self.summary_writer = SummaryWriter(log_dir=log_dir)

        self.epoch = args.start_epoch
        # Current iteration in epoch (i.e., # examples seen in the current epoch)
        self.iter = 0
        # Current iteration overall (i.e., total # of examples seen)
        self.global_step = round_down((self.epoch - 1) * dataset_len, args.batch_size)
        self.iter_start_time = None
        self.epoch_start_time = None
        self.un_normalize = util.UnNormalize(CATAL_MEAN, CATAL_STD)

    def _log_scalars(self, scalar_dict, print_to_stdout=True):
        """Log all values in a dict as scalars to TensorBoard."""
        for k, v in scalar_dict.items():
            if print_to_stdout:
                self.write('[{}: {:.3g}]'.format(k, v))
            k = k.replace('_', '/')
            self.summary_writer.add_scalar(k, v, self.global_step)

    def write(self, message, print_to_stdout=True):
        """Write a message to the log. If print_to_stdout is True, also print to stdout."""
        with open(self.log_path, 'a') as log_file:
            log_file.write(message + '\n')
        if print_to_stdout:
            print(message)

    def visualize(self, inputs, logits, targets, paths, phase):
        num_visualized = 0

        probs = F.softmax(logits.detach().to('cpu'), dim=-1).numpy()
        if targets is not None:
            targets = targets.detach().to('cpu').numpy()

        for i in range(self.num_visuals):
            if i >= inputs.shape[0]:
                break

            # Get input, output, and label
            input_np = self.un_normalize(inputs[i])
            if targets is None:
                label = 'no_label'
            elif targets[i].any():
                label = 'positive'
            else:
                label = 'negative'
            prob_np = probs[i]

            # Log to tensorboard
            img_name = os.path.basename(paths[i])
            tag = '{}/{}/prob_{:.4f}/{}'.format(phase, label, prob_np[1], img_name)
            self.summary_writer.add_image(tag, input_np, self.global_step)

            num_visualized += 1

        return num_visualized

    def start_iter(self):
        """Log info for start of an iteration."""
        raise NotImplementedError

    def end_iter(self):
        """Log info for end of an iteration."""
        raise NotImplementedError

    def start_epoch(self):
        """Log info for start of an epoch."""
        raise NotImplementedError

    def end_epoch(self, metrics):
        """Log info for end of an epoch. Save model parameters and update learning rate."""
        raise NotImplementedError
