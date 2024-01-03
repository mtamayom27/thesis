import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from system.bio_model.gridcellModel import GridCellNetwork
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network
from system.bio_model.placecellModel import PlaceCellNetwork
from system.bio_model.cognitivemap import LifelongCognitiveMap, CognitiveMapInterface
import system.plotting.plotResults as plot

plotting = True  # if True: plot paths
debug = True  # if True: print debug output


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


def waypoint_movement(path, env_model: str, gc_network: GridCellNetwork, pc_network: PlaceCellNetwork, cognitive_map: CognitiveMapInterface):
    """ Agent navigates on path, 
        exploring the environment and building the cognitive map
    
    arguments:
    path        -- initial start position and subgoals on the path
    env_model   -- environment model
    re_type     -- type of reachability used to connect the place cells on the cognitive map    
    """

    # get the path through the environment
    mapLayout = MapLayout(env_model)
    goals = []
    for i in range(len(path) - 1):
        new_wp = mapLayout.find_path(path[i], path[i + 1])
        if new_wp is None:
            raise ValueError("No path found!")
        goals += new_wp
        if plotting:
            mapLayout.draw_map_path(path[i], path[i + 1], i)

    # draw the path
    if plotting:
        mapLayout.draw_path(goals)

    env = PybulletEnvironment(False, 1e-2, env_model, "analytical", build_data_set=True, start=path[0])

    # The local controller navigates the path analytically and updates the pc_netowrk and the cognitive_map
    for i, goal in enumerate(goals):
        print_debug(f"new waypoint with coordinates {goal}.", f'{i / len(goals) * 100} % completed.')
        vector_navigation(env, goal, gc_network, model="analytical", step_limit=5000, obstacles=False,
                          plot_it=False, exploration_phase=True, pc_network=pc_network, cognitive_map=cognitive_map)
        if plotting and (i + 1) % 100 == 0:
            cognitive_map.draw()
            cognitive_map.save(filename="partial_with_cleanup.gpickle")
            plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=False)

    cognitive_map.draw()
    cognitive_map.save(filename="partial_with_cleanup.gpickle")
    plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=False)

    # plot the trajectory
    # if plotting:
    #     plot.plotTrajectoryInEnvironment(env, pc_network=pc_network)
    env.end_simulation()
    # cognitive_map.postprocess()
    return pc_network, cognitive_map


def get_path_re():
    """ returns path to RE model folder """
    dirname = os.path.join(os.path.dirname(__file__), "../controller/reachability_estimator/data/models")
    return dirname


def exploration_path(env_model, creation_type, connection_type, weights_file):
    """ Agent follows a hard-coded path to explore
        the environment and build the cognitive map.

        arguments:
        - env_model: environment to be explored
        - creation_type, connection_type, connection: see cognitive map

    """

    # TODO Johanna: Future Work: add exploration patterns for all mazes
    if env_model == "Savinov_val3":
        goals = [
            # [-2, 0], [-6, -2.5], [-4, 0.5], [-6.5, 0.5], [-7.5, -2.5], [-2, -1.5], [1, -1.5],
            [0.5, 1.5], [2.5, -1.5], [1.5, 0], [5, -1.5]
            # , [4.5, -0.5], [-0.5, 0], [-8.5, 3], [-8.5, -4],
            # [-7.5, -3.5], [1.5, -3.5], [-6, -2.5]
        ]

    elif env_model == "Savinov_val2":
        pass
    elif env_model == "Savinov_test7":
        pass

    # explore and generate
    # Setup grid cells, place cells and the cognitive map
    gc_network = setup_gc_network(1e-2)
    pc_network = PlaceCellNetwork(re_type=creation_type, weights_file=weights_file)

    # TODO: add setting
    # cognitive_map = CognitiveMap(re_type=connection_type, connection=connection, env_model=env_model)
    cognitive_map = LifelongCognitiveMap(re_type=connection_type, env_model=env_model, weights_file=weights_file, with_spikings=True)

    pc_network, cognitive_map = waypoint_movement(goals, env_model, gc_network, pc_network, cognitive_map)

    # save place cell network and cognitive map
    pc_network.save_pc_network()
    cognitive_map.save()

    # draw the cognitive map
    if plotting:
        cognitive_map.draw()


if __name__ == "__main__":
    """ 
    Create a cognitive map by exploring the environment
    Choose creation and connection as is suitable

    See cognitivemap.py for description:
    - creation_re_type: "firing", "neural_network", "distance", "simulation", "view_overlap"
    - connection_re_type: "firing", "neural_network", "distance", "simulation", "view_overlap"
    """

    creation_re_type = "firing"
    connection_re_type = "neural_network"
    weights_file = "no_siamese_mse.50"

    exploration_path("Savinov_val3", creation_re_type, connection_re_type, weights_file)

# distance - nn
# remaining nodes: [array([-3.98071443,  0.42070829]), array([-6.49144431,  0.46288753]), array([-7.53156786, -1.17549649]), array([-7.4966087 , -1.67753694]), array([-4.8007405 , -0.58218752]), array([-5.16533894, -0.2361713 ]), array([-6.34168938,  0.94021901]), array([-5.27333001,  2.58988583]), array([-5.12343086,  1.62604299]), array([-4.62003059,  1.60697773]), array([-4.11643896,  1.60351844]), array([-3.61587788,  1.59418923]), array([-2.6451231 ,  1.81508918]), array([-3.28434639,  2.36336196]), array([-3.78375993,  2.33473248]), array([-3.8219019 ,  3.36893061]), array([-2.32084831,  3.34734948]), array([1.38069465, 1.93898345]), array([5.24412453, 3.15211453]), array([4.74931109, 2.32124329]), array([4.24870451, 2.3588828 ]), array([3.74276442, 2.35064785]), array([2.72195519, 2.22078851]), array([3.93542189, 0.49713093]), array([5.31059941, 0.81943853]), array([ 5.29684333, -0.68805799]), array([-1.31103609,  2.85208299]), array([-0.99179856,  2.46315127]), array([-0.35820253,  1.22622687]), array([-0.35229931,  0.72324332]), array([-0.34595267,  0.22121126]), array([-0.35329206, -0.27882235]), array([-0.35128234, -2.28597496]), array([-0.19702614, -3.26435169]), array([ 1.60055036, -2.61493285]), array([ 2.10089116, -2.65781199]), array([ 2.49672217, -2.9642148 ]), array([ 2.84202634, -3.33039538]), array([ 5.00133115, -2.52229256]), array([ 4.53726454, -2.33380373]), array([ 3.79848258, -0.64089242]), array([ 4.27687952, -0.48661372]), array([-7.55591314,  1.62758217]), array([-8.4983013 ,  2.78433602]), array([-8.34688653, -0.04861782]), array([-7.89731691, -2.47973943]), array([-8.52759811, -3.24554776]), array([-8.22255847, -4.16898255]), array([-7.74296407, -4.31065231]), array([-7.24270822, -4.28886209]), array([-6.73981107, -4.3081583 ]), array([-6.23686363, -4.29655259]), array([-5.73535571, -4.29949396]), array([-5.23506146, -4.30081188]), array([-5.24372016, -3.48330596]), array([-5.74630521, -3.51280506]), array([-6.24605539, -3.49468669]), array([-6.74611524, -3.50256643]), array([-7.24921207, -3.50087806]), array([-1.5792878 , -4.29488454]), array([-0.5783866 , -4.30426594]), array([ 0.42538952, -4.30128635]), array([ 1.51990851, -3.5777774 ]), array([-3.2311994 , -2.47856839])]

# firing - nn
#remaining nodes: [array([-7.52790074, -1.32487306]), array([-7.54669971, -2.44801042]), array([-7.32010824, -2.20040571]), array([-7.3335411 , -1.97186294]), array([-7.34506411, -1.86281645]), array([-7.361226  , -1.66226236]), array([-2.23705314, -1.5009451 ]), array([-5.20036055, -0.20324482]), array([-5.31551217, -0.09203262]), array([-5.53147156,  0.12732284]), array([-5.93046529,  0.53415442]), array([-6.05040138,  0.6522018 ]), array([-6.24141637,  0.84056787]), array([-6.97816256,  3.38189209]), array([-5.90471632,  3.35569551]), array([-5.31537036,  2.89019648]), array([-5.27156744,  2.63407664]), array([-4.71702621,  1.59562195]), array([-4.33959136,  1.61572019]), array([-3.47608439,  1.59850771]), array([-2.63136929,  1.83995978]), array([-3.01918951,  2.38108586]), array([-3.28045464,  2.36380184]), array([-1.35049143,  3.35300885]), array([0.62063352, 2.63302299]), array([0.81633447, 1.64651359]), array([5.22247666, 3.17640549]), array([4.57933497, 2.32931541]), array([4.27202169, 2.35757603]), array([3.91670832, 2.35842348]), array([3.64397927, 2.34676806]), array([2.98176485, 1.43800566]), array([ 1.02575037, -1.43784352]), array([ 1.02874026, -1.43509002]), array([ 2.35781849, -0.09003252]), array([5.07467855, 3.32292456]), array([4.68409829, 3.3569324 ]), array([4.37490739, 3.3321057 ]), array([4.24934966, 3.33556794]), array([4.24219549, 3.33586235]), array([4.1818227 , 3.33969241]), array([4.12068723, 3.34420394]), array([3.93207229, 3.35566383]), array([3.77751905, 3.3583624 ]), array([3.53401793, 3.3538062 ]), array([3.37069642, 3.3485522 ]), array([3.36672142, 3.34845207]), array([3.35857963, 3.34820126]), array([3.35462984, 3.34809163]), array([3.35079043, 3.3479854 ]), array([3.23476586, 3.3456493 ]), array([3.05477776, 3.34495418]), array([2.79340654, 3.348323  ]), array([1.09082259, 1.54831724]), array([0.83867925, 1.47332543]), array([0.51107536, 1.50596058]), array([0.51112306, 1.50568541]), array([0.51119853, 1.50551525]), array([0.51148973, 1.50535278]), array([0.51194009, 1.50531725]), array([0.51240353, 1.50534622]), array([0.51303545, 1.50536189]), array([0.54173326, 1.51289387]), array([5.1279461 , 3.24371187]), array([4.68721293, 2.31733896]), array([4.4250918 , 2.34819142]), array([4.18607309, 2.36692228]), array([3.83964332, 2.35335374]), array([2.92467444, 1.49656681]), array([ 2.49675507, -1.23338683]), array([ 2.52323273, -1.45541055]), array([5.31595166, 1.10967753]), array([ 4.99484405, -1.42024783]), array([ 5.05340327, -1.37316256]), array([ 5.28082404, -0.45769833]), array([ 5.29929755, -0.11329063]), array([4.68424322, 1.25964247]), array([3.30831261, 1.10795651]), array([4.62033366, 3.35678815]), array([4.4695561 , 3.34360503]), array([4.46562859, 3.34335999]), array([4.46157999, 3.34307793]), array([4.45759704, 3.34281075]), array([4.45367967, 3.34256343]), array([4.44986689, 3.34233196]), array([4.44271952, 3.34191681]), array([4.43915677, 3.34167788]), array([4.43547823, 3.34147463]), array([4.431816  , 3.34127594]), array([4.42798713, 3.34103731]), array([4.42417123, 3.340816  ]), array([4.42022668, 3.3406306 ]), array([4.41627983, 3.34045481]), array([4.41221166, 3.34024971]), array([4.4081966 , 3.34006385]), array([4.40427316, 3.33988957]), array([4.40042913, 3.33972782]), array([4.37055177, 3.338549  ]), array([4.36642502, 3.33842792]), array([4.3623407 , 3.33830236]), array([4.35830991, 3.33817566]), array([4.27634857, 3.33672644]), array([4.03320294, 3.34488178]), array([3.73456577, 3.35578353]), array([3.37176395, 3.35177232]), array([3.0689523 , 3.34796907]), array([2.66972677, 3.35063253]), array([1.56900534, 2.96923226]), array([1.59818609, 2.66206214]), array([-0.07502728,  3.37642099]), array([-0.42483474,  3.34334426]), array([-1.04387901,  2.52073475]), array([-0.80905245,  2.28732859]), array([-0.36587098,  1.87526265]), array([-0.3218599,  1.6266576]), array([-0.34122124,  1.38924818]), array([-0.36065018,  1.19206138]), array([-0.36441896,  0.9801674 ]), array([-0.35184902,  0.71554865]), array([-0.34304797,  0.44211658]), array([-0.34846791,  0.11957922]), array([-0.35293041, -0.15697527]), array([-0.35218441, -0.46393582]), array([-0.34993861, -0.71854836]), array([-0.3492961 , -0.98425422]), array([-0.34883754, -1.29559179]), array([-0.34931642, -1.62144074]), array([-0.34997846, -1.82177838]), array([-0.35079229, -2.01545648]), array([-0.35123382, -2.32699548]), array([-0.22042206, -3.23819973]), array([ 2.20720076, -2.73052583]), array([ 2.52435655, -2.99067149]), array([ 4.07057779, -4.33037271]), array([ 3.56883682, -1.95638618]), array([ 3.93709964, -0.49276122]), array([ 4.28087465, -0.48700456]), array([ 4.49991404, -0.49759209]), array([ 3.57818556, -1.08026109]), array([ 3.60248595, -1.33268298]), array([ 3.10800567, -3.55059059]), array([ 2.47361445, -3.00076497]), array([ 1.92440564, -2.57036929]), array([ 1.68883611, -2.59945239]), array([-0.52637902, -2.93500544]), array([-0.48637583, -2.32673212]), array([-0.67684925,  0.32370822]), array([-0.65251319,  0.58699346]), array([-0.63583309,  0.84744806]), array([-0.65601854,  1.42554189]), array([-0.65262225,  1.6849226 ]), array([-1.336066  ,  2.83393874]), array([-1.53778067,  3.02163536]), array([-2.11302063,  3.36866634]), array([-2.44062621,  3.3284142 ]), array([-2.76032859,  3.34332624]), array([-3.07469313,  3.36091697]), array([-4.31279737,  2.85375863]), array([-3.02812768,  1.56999921]), array([-3.37621275,  1.60573634]), array([-3.80650735,  1.60613663]), array([-4.17699702,  1.59164741]), array([-5.5482515 ,  2.47111685]), array([-5.87042127,  3.38213183]), array([-6.09202938,  3.37805169]), array([-7.56468855,  2.55632251]), array([-7.55599928,  1.4792246 ]), array([-8.52154254,  1.11693521]), array([-8.5259298 ,  2.80830999]), array([-8.51071339,  2.50499086]), array([-8.49105944,  2.27109925]), array([-8.49060878,  1.98021247]), array([-8.50666989,  1.59141509]), array([-8.49881266,  0.65816493]), array([-8.50310626,  0.42761422]), array([-8.50833665,  0.16777327]), array([-8.29491907, -0.12257633]), array([-7.53813727, -0.86343436]), array([-7.52120402, -1.02803527]), array([-7.54011151, -1.32207477]), array([-7.85055825, -2.42806825]), array([-8.53048919, -3.17493229]), array([-8.51468772, -3.44339338]), array([-8.30944922, -4.09801153]), array([-7.83970693, -4.32171724]), array([-7.48957345, -4.28776479]), array([-7.20408581, -4.29093771]), array([-7.07448812, -4.2986082 ]), array([-6.86195998, -4.30709431]), array([-6.612566  , -4.30586195]), array([-6.31269474, -4.29774828]), array([-6.02830586, -4.29644301]), array([-5.70025871, -4.29979858]), array([-5.35472751, -4.30077911]), array([-5.14017134, -3.47478183]), array([-5.43916195, -3.50246531]), array([-5.68516573, -3.51364897]), array([-6.0254169 , -3.50108294]), array([-6.51341971, -3.49764253]), array([-6.93715306, -3.50330812]), array([-7.30983499, -3.50040556]), array([-7.48318324, -3.49928274]), array([-2.58894713, -3.82885589]), array([-1.97026416, -4.3305289 ]), array([-1.85946503, -4.32366322]), array([-1.67057113, -4.30379243]), array([-1.40405116, -4.28589764]), array([-1.12464035, -4.29452976]), array([-0.95341827, -4.30352588]), array([-0.71902477, -4.30743362]), array([-0.43825885, -4.30013671]), array([-0.11068385, -4.29673362]), array([ 0.0952654 , -4.29841187]), array([ 0.28851098, -4.30051317]), array([ 0.59270637, -4.30195877]), array([ 1.53339294, -3.86411499]), array([ 1.52095494, -3.7134349 ]), array([ 1.53612007, -3.51893953]), array([ 1.53585817, -3.51919647]), array([ 1.535423  , -3.51958387]), array([ 1.5338874 , -3.52165806]), array([ 1.48285114, -3.57963846]), array([ 1.02295803, -4.33202071]), array([ 0.91014644, -4.32790397]), array([ 0.6821082 , -4.30758573]), array([ 0.52837129, -4.29308125]), array([ 0.48244787, -4.29015024]), array([ 0.4785307 , -4.28991435]), array([ 0.47461381, -4.2896965 ]), array([ 0.4706923 , -4.28949442]), array([ 0.46666677, -4.28931895]), array([ 0.46254392, -4.28912377]), array([ 0.45849968, -4.28894591]), array([ 0.45455117, -4.28878467]), array([ 0.45071705, -4.28863888]), array([ 0.44697863, -4.28848191]), array([ 0.439982  , -4.28821997]), array([ 0.43649893, -4.28808087]), array([ 0.43302049, -4.28795118]), array([ 0.42926055, -4.28781352]), array([ 0.42550187, -4.28768926]), array([ 0.29251663, -4.28711666]), array([ 0.28525592, -4.28727572]), array([ 0.28149011, -4.28736703]), array([ 0.27772972, -4.28746409]), array([ 0.17828671, -4.29118627]), array([ 0.10856518, -4.29503542]), array([ 0.10463344, -4.29524133]), array([ 0.10080149, -4.295443  ]), array([ 0.09360785, -4.29577289]), array([ 0.0900587 , -4.29598341]), array([ 0.08637283, -4.29624701]), array([ 0.08255613, -4.29646968]), array([ 0.07874035, -4.29669424]), array([ 0.07492226, -4.29691611]), array([ 0.07094858, -4.29716709]), array([ 0.06685263, -4.29738442]), array([ 0.0627611 , -4.29759608]), array([ 0.05871658, -4.29779715]), array([ 0.05477616, -4.29798749]), array([ 0.0509401 , -4.29818257]), array([ 0.04372688, -4.29850168]), array([ 0.04015926, -4.29869918]), array([ 0.03645936, -4.29893838]), array([ 0.03262418, -4.29913281]), array([ 0.02880452, -4.29932816]), array([ 0.02499386, -4.29951633]), array([ 0.02103202, -4.29973547]), array([ 0.01694671, -4.29991823]), array([ 0.01286416, -4.30009803]), array([ 0.00882395, -4.30027981]), array([ 0.00486763, -4.30046396]), array([ 1.02174525e-03, -4.30063731e+00]), array([-2.73891364e-03, -4.30080699e+00]), array([-0.02819568, -4.3019767 ]), array([-0.19957139, -4.30647367]), array([-0.47925132, -4.3035292 ]), array([-1.13716949, -4.29906701]), array([-1.40603228, -4.30140823]), array([-1.63737713, -4.30134997]), array([-2.67699322, -3.63947797]), array([-2.64663882, -3.36724559]), array([-6.28031161,  0.50114265])]
