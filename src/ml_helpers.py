import random
import torch
import torch.nn as nn
import torch.nn.functional as F

from collections import namedtuple

Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward'))

def optimize_model(
        policy_net,
        target_net,
        device,
        optimizer,
        transitions,
        batch_size,
        reward_decay):
    if (len(transitions)  < batch_size):
        return

    transitions = random.sample(transitions, batch_size)
    batch = Transition(*zip(*transitions))
    state_batch = torch.cat(batch.state)
    action_batch = torch.cat(batch.action)
    reward_batch = torch.cat(batch.reward)

    predicted_actions = policy_net(state_batch)

    state_action_values = predicted_actions.gather(1, action_batch.unsqueeze(-1))

    next_state_values = target_net(state_batch).max(1)[0].detach()
    expected_state_action_values = (next_state_values * reward_decay) + reward_batch
    loss = F.smooth_l1_loss(state_action_values, expected_state_action_values.unsqueeze(1))

    optimizer.zero_grad()
    loss.backward()

    for param in policy_net.parameters():
        param.grad.data.clamp_(-1, 1)
    optimizer.step()

    return loss.data.item()


class LSTM_DQN(nn.Module):
    """This the model we'll be using our Q Function"""
    def __init__(self, config, device, use_cuda=False):
        super(LSTM_DQN,self).__init__()

        self.device = device
        self.W = nn.LSTM(config["input_dim"], config["hidden_dim"],batch_first=True,bidirectional=config["bidirectional"], num_layers=config["num_layers"])
        if config["bidirectional"]:
            self.h0, self.c0 = (torch.zeros(2 * config["num_layers"], 1, config["hidden_dim"], device=device),
                    torch.zeros(2 * config["num_layers"], 1, config["hidden_dim"], device=device))
            self.U = nn.Linear(config["hidden_dim"] * 2,config["output_dim"])
        else:
            self.h0, self.c0 = (torch.zeros(config["num_layers"], 1, config["hidden_dim"], device=device),
                    torch.zeros(config["num_layers"], 1, config["hidden_dim"], device=device))
            self.U = nn.Linear(config["hidden_dim"],config["output_dim"])
        
        # if use_cuda:
        #     self.h0.cuda()
        #     self.c0.cuda()

        for param in self.W.parameters():
            if len(param.size()) > 1:
                nn.init.orthogonal_(param)

        for param in self.U.parameters():
            if len(param.size()) > 1:
                nn.init.orthogonal_(param)

        self.config = config

    def forward(self, x):
        # apply LSTM
        batch_len, _, _ = x.size()

        h0 = self.h0.repeat(1, batch_len, 1).to(device=self.device)
        c0 = self.c0.repeat(1, batch_len, 1).to(device=self.device)

        out, _ = self.W(x, (h0,c0))

        return self.U(out[:,-1,:])
