def add_arguments(parser):
    '''
    Add your arguments here if needed. The TAs will run test.py to load
    your default arguments.

    For example:
        parser.add_argument('--batch_size', type=int, default=32, help='batch size for training')
        parser.add_argument('--learning_rate', type=float, default=0.01, help='learning rate for training')
    '''
    parser.add_argument('--render', action='store_true', help='whether to render pong')
    parser.add_argument('--timestamp', required=False, help='timestamp used to name saved models and tensorboard logs')
    parser.add_argument('--checkpoint', help='load previously trained checkpoint')
    return parser
