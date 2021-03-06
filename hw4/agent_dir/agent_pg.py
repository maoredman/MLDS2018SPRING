import scipy, torch, cv2, time, os, random, json
import numpy as np
import matplotlib.pyplot as plt
from agent_dir.agent import Agent
from torch.autograd import Variable

def prepro(I):
    """
    Call this function to preprocess RGB image to grayscale image if necessary
    This preprocessing code is from
        https://github.com/hiwonjoon/tf-a3c-gpu/blob/master/async_agent.py
    
    Input: 
    RGB image: np.array
        RGB screen of game, shape: (210, 160, 3)
    Default return: np.array 
        Grayscale image, shape: (80, 80)
    
    """
    # image = 0.2126 * data[:, :, 0] + 0.7152 * data[:, :, 1] + 0.0722 * data[:, :, 2] # grayscale
    # image = image[30:,:] # remove scoreboard
    # image = cv2.resize(image, dsize=image_size, interpolation=cv2.INTER_CUBIC) # resize to (80, 80)
    # image = np.expand_dims(image, axis=0) # (1, 80, 80)
    # # print('IMAGE SHAPE', image.shape)
    # return image

    I = I[35:195]
    I = I[::2, ::2, 0]
    I[I == 144] = 0
    I[I == 109] = 0
    I[I != 0 ] = 1
    return I.astype(np.float).ravel()

# if torch.cuda.is_available():
#     torch.cuda.manual_seed(77)
# else:
#     torch.manual_seed(77)

class Policy(torch.nn.Module):
    def __init__(self, gamma=0.99, lr=1e-4, rmsprop_decay=0.99):
        super(Policy, self).__init__()

        # ========== CONVNET ==========
        # self.conv1 = torch.nn.Conv2d(in_channels=1, out_channels=16, kernel_size=3) # (batch_size, 16, 208, 158)
        # self.conv2 = torch.nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3) # (batch_size, 32, 206, 156)
        # self.fc1 = torch.nn.Linear(32 * 76 * 76, 64)
        # self.fc2 = torch.nn.Linear(64, 32)
        # self.fc3 = torch.nn.Linear(32, 3) # 6 actions to choose from, only taking 3 here
        # known actions: 1(no move), 2(up), 3(down)
        # ========== CONVNET ==========

        self.fc4 = torch.nn.Linear(80*80, 256)
        self.fc5 = torch.nn.Linear(256, 256)
        self.fc6 = torch.nn.Linear(256, 3) # known actions: 1(no move), 2(up), 3(down)

        self.gamma = gamma
        self.lr = lr
        self.rmsprop_decay = rmsprop_decay
        
        self.output2action = {0: 1, 1: 2, 2: 3}
        self.saved_log_probs = []
        self.rewards = []
        
    def forward(self, x): # x: np.array (1, 80, 80)
        # ========== CONVNET ==========
        # x = x.reshape(-1, 1, 80, 80) # (batch_size, channels, ...)
        # x = Variable(torch.Tensor(x))
        # if torch.cuda.is_available():
        #     x = x.cuda()
        # x = self.conv1(x)
        # x = self.conv2(x)
        # x = torch.nn.functional.relu(x)
        # x = x.view(-1, 32*76*76)
        # x = self.fc1(x) # TODO: add batch norm?
        # x = torch.nn.functional.relu(x)
        # x = self.fc2(x)
        # x = torch.nn.functional.relu(x)
        # x = self.fc3(x)
        # ========== CONVNET ==========

        y = x.view(-1, 80*80)
        y = self.fc4(y) # TODO: add batch norm?
        y = torch.nn.functional.selu(y)
        y = self.fc5(y)
        y = torch.nn.functional.selu(y)
        y = self.fc6(y)

        action_probs = torch.nn.functional.softmax(y, dim=1)
        return action_probs # (batch_size, 6)

    def reset(self):
        self.saved_log_probs = []
        self.rewards = []


class Agent_PG(Agent):
    def __init__(self, env, args):
        """
        Initialize every things you need here.
        For example: building your model
        """

        super(Agent_PG,self).__init__(env)

        # self.time_step = time_step # TODO: delete this
        self.saved_model_path = './model_pg.pth' # TODO: change this
        self.loaded_model = None
        self.loaded_observation_old = False
        self.observation_old = None

        if args.test_pg:
            #you can load your model here
            print('loading trained model')
            loaded_model = Policy()
            if torch.cuda.is_available():
                loaded_model.load_state_dict(torch.load(self.saved_model_path))
                self.loaded_model = loaded_model.cuda()
            else:
                loaded_model.load_state_dict(torch.load(self.saved_model_path, map_location=lambda storage, loc: storage))
                self.loaded_model = loaded_model

        ##################
        # YOUR CODE HERE #
        ##################


    def init_game_setting(self): # NOTE: run at beginning of new episode, during test time only
        """

        Testing function will call this function at the begining of new game
        Put anything you want to initialize if necessary

        """
        ##################
        # YOUR CODE HERE #
        ##################
        self.loaded_observation_old = False
        self.observation_old = None


    def train(self, render, timestamp, checkpoint): # NOTE: supposing batch_size=1
        """
        Implement your training algorithm here
        """
        ##################
        # YOUR CODE HERE #
        ##################
        from tensorboardX import SummaryWriter

        policy = Policy()

        if checkpoint: # Resume training from previously saved model params
            print('Resuming training from', checkpoint)
            if torch.cuda.is_available():
                policy.load_state_dict(torch.load(checkpoint))
            else:
                policy.load_state_dict(torch.load(checkpoint, map_location=lambda storage, loc: storage))

        policy.train()
        if torch.cuda.is_available():
            print('Using CUDA')
            policy = policy.cuda()
        else:
            print('Not using CUDA')
        
        optimizer = torch.optim.RMSprop(policy.parameters(), lr=policy.lr, weight_decay=policy.rmsprop_decay)
        # optimizer_random_action = torch.optim.RMSprop(policy.parameters(), lr=policy.lr/1e4, weight_decay=policy.rmsprop_decay)
        writer = SummaryWriter()
        for i_episode in range(10**7): # 21 points/reward per episode, ~6000 episodes to reach baseline?
            policy.reset()
            # if i_episode < policy.random_action_episodes:
            #     optimizer_random_action.zero_grad()
            # else:
            #     optimizer.zero_grad()
            optimizer.zero_grad()

            observation_old = prepro(self.env.reset()) # NOTE: observation_old is always prepro()
            observation = self.env.reset() # NOTE: observation is always "raw"

            a = time.time()
            for t in range(10000): # usually done in around 1000 steps
                if render:
                    self.env.env.render()

                observation = prepro(observation)
                observation_delta = observation - observation_old
                observation_old = observation # NOTE: overwrite observation_old

                observation_delta = torch.from_numpy(observation_delta).float().unsqueeze(0)
                observation_delta = Variable(observation_delta)
                if torch.cuda.is_available():
                     observation_delta = observation_delta.cuda()
                action_probs = policy(observation_delta) # (batch_size, 3)
                # print('ACTION_PROBS:', action_probs)

                action_sampler = torch.distributions.Categorical(action_probs)
                # action = int(torch.max(policy_output, dim=1)[1].data) # torch.max returns (max val, argmax)
                action_pre = action_sampler.sample() # NOTE: taking subset of env's action space, need to convert
                # print('POLICY ACTION:', action_pre)
                policy.saved_log_probs.append(action_sampler.log_prob(action_pre))

                action_real = policy.output2action[int(action_pre)] # NOTE: converting to env's action space
                observation, reward, done, info = self.env.step(action_real) # NOTE: overwrite observation
                policy.rewards.append(reward)

                if torch.cuda.is_available():
                    if (t+1)%1000 == 0:
                        print('Ran {} timesteps'.format(t+1))
                else:
                    if (t+1)%100 == 0:
                        print('Ran {} timesteps'.format(t+1))

                if done:
                    print("Episode finished after {} timesteps".format(t+1))
                    break

            if not done:
                print('Terminated episode after running for 10000 steps')

            R = 0
            R_raw = 0
            policy_loss = []
            rewards = []
            print('Calculating rewards and loss function values...')
            for r in policy.rewards[::-1]:
                # if r == 1 or r == -1:
                #     R = 0
                R = r + policy.gamma * R
                R_raw = r + R_raw
                rewards.insert(0, R)
            rewards = torch.Tensor(rewards)
            rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-10)

            # writer.add_scalar('./{}/reward'.format(timestamp), R, i_episode+1)
            writer.add_scalar('{}/reward_raw'.format(timestamp), R_raw, i_episode+1)
            
            json_log_dir = './{}'.format(timestamp) # NOTE: this part should be outside for loop, but here is convenient for debugging
            if not os.path.exists(json_log_dir):
                os.makedirs(json_log_dir)
            json_data = {'reward_raw': R_raw}
            with open("{}/{}-reward.json".format(json_log_dir, i_episode+1), 'w') as outfile:
                json.dump(json_data, outfile, sort_keys=True, indent=4)

            # ========== ORIGINAL VERSION ========== 
            for log_prob, reward in zip(policy.saved_log_probs, rewards):
                # policy_loss.append(-log_prob * reward)
                single_loss = -log_prob * reward
                single_loss.backward()
            # ========== ORIGINAL VERSION ========== 


            # ========== VANILLA VERSION ========== 
            # for log_prob in policy.saved_log_probs:
            #     # policy_loss.append(-log_prob * reward)
            #     single_loss = -log_prob * R_raw
            #     single_loss.backward()
            # ========== VANILLA VERSION ========== 
        

            # policy_loss = torch.cat(policy_loss).sum() # NOTE: doing this may cause OOM on GPU
            # print('Doing all backprops...')
            # policy_loss.backward()

            for idx, param in enumerate(policy.parameters()):
                if idx == 0:
                    print('GRADIENTS [0]:')
                    print(param.grad)
                if idx == 2:
                    print('GRADIENTS [2]:')
                    print(param.grad)
                    break

            # if i_episode < policy.random_action_episodes:
            #     optimizer_random_action.step()
            # else:
            #     optimizer.step()
            optimizer.step()

            del policy.rewards[:]
            del policy.saved_log_probs[:]
            

            print('[Episode {}: {} minutes] Reward is {}    Reward_raw is {}'.format(i_episode+1, (time.time()-a)/60, R, R_raw))
            
            if (i_episode+1) % 200 == 0:
                model_dir = './models/{}'.format(timestamp)
                if not os.path.exists(model_dir):
                    os.makedirs(model_dir)
                torch.save(policy.state_dict(), '{}/episode{}.pth'.format(model_dir, i_episode+1))
                print('Saved model!')

            print('======================')


    def make_action(self, observation, test=True): # used during test time
        """
        Return predicted action of your agent

        Input:
            observation: np.array
                current RGB screen of game, shape: (210, 160, 3)

        Return:
            action: int
                the predicted action from trained model
        """
        ##################
        # YOUR CODE HERE #
        ##################
        if not self.loaded_observation_old:
            self.loaded_observation_old = True
            self.observation_old = prepro(observation)

        observation = prepro(observation)

        observation_delta = observation - self.observation_old
        observation_delta = torch.from_numpy(observation_delta).float().unsqueeze(0)
        observation_delta = Variable(observation_delta)
        if torch.cuda.is_available():
             observation_delta = observation_delta.cuda()

        action_probs = self.loaded_model(observation_delta)
        
        # ========= ARGMAX ========= 
        action_pre = torch.max(action_probs, dim=1)[1]
        # ========= ARGMAX ========= 

        # ========= SAMPLING ========= 
        # action_sampler = torch.distributions.Categorical(action_probs)
        # action_pre = action_sampler.sample()
        # ========= SAMPLING ========= 
        
        action_real = self.loaded_model.output2action[int(action_pre)]

        self.observation_old = observation

        return action_real
        # return self.env.get_random_action()

