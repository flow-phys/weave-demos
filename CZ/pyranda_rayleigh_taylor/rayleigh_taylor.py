import argparse
import sys
import textwrap
import numpy
import matplotlib.pyplot as plt
from matplotlib import cm

from pyranda import pyrandaSim, pyrandaBC, pyrandaTimestep


def run_sim(args):
    Npts = args.num_points
    dim = args.dim

    if dim == "2D":
        is2D = True
    elif dim == "3D":
        is2D = False
    else:
        raise ValueError(f"Unknown dim value '{dim}'")

    if 'seed' in args:
        random_ic_seed = args.seed
    else:
        random_ic_seed = None

    headless = args.headless

    ## Define a mesh
    if is2D:
        problem = "RAYLEIGH_TAYLOR_2D"
        imesh = (
            """
        xdom = (0.0, 2.8*pi , int(Npts*1.4), periodic=False)
        ydom = (0.0, 2*pi*FF,  Npts, periodic=True)
        zdom = (0.0, 2*pi*FF,  1, periodic=True)
        """.replace(
                "Npts", str(Npts)
            )
            .replace("pi", str(numpy.pi))
            .replace("FF", str(float(Npts - 1) / Npts))
        )
        waveLength = 4
    else:
        problem = "RAYLEIGH_TAYLOR_3D"
        imesh = (
            """
        xdom = (0.0, 3.0*pi , int(Npts*1.5), periodic=False)
        ydom = (0.0, 2*pi*FF,  Npts, periodic=True)
        zdom = (0.0, 2*pi*FF,  Npts, periodic=True)
        """.replace(
                "Npts", str(Npts)
            )
            .replace("pi", str(numpy.pi))
            .replace("FF", str(float(Npts - 1) / Npts))
        )
        waveLength = 4

    rho_l = 1.0  # Density of light fluid
    rho_h = 3.0  # Density of heavy fluid
    mwH = 3.0  # Mixing width heavy/light parameters?
    mwL = 1.0
    gx = (
        -0.01
    )  # NOTE: is this gravity?  if so lets switch to y to cutout using vist transforms to rotate
    Runiv = 1.0  #
    CPh = 1.4
    CVh = 1.0
    CPl = 1.4
    CVl = 1.0

    parm_dict = {
        "gx": gx,
        "CPh": CPh,
        "CPl": CPl,
        "CVh": CVh,
        "CVl": CVl,
        "mwH": mwH,
        "mwL": mwL,
        "Runiv": Runiv,
        "waveLength": waveLength,
        "rho_l": rho_l,
        "rho_h": rho_h,
        "delta": 2.0 * numpy.pi / Npts * 4,
    }

    # Initialize a simulation object on a mesh
    ss = pyrandaSim(problem, textwrap.dedent(imesh))
    ss.addPackage(pyrandaTimestep(ss))
    ss.addPackage(pyrandaBC(ss))

    # User defined function to take mean of data and return it as 3d field, dataBar
    def meanXto3d(pysim, data):
        meanX = pysim.PyMPI.yzsum(data) / (pysim.PyMPI.ny * pysim.PyMPI.nz)
        tmp = pysim.emptyScalar()
        for i in range(tmp.shape[0]):
            ii = int(pysim.mesh.indices[0].data[i, 0, 0])
            tmp[i, :, :] = meanX[ii]
        return tmp

    ss.addUserDefinedFunction("xbar", meanXto3d)

    # Define the equations of motion
    eom = """
    # Primary Equations of motion here
    ddt(:rhoYh:)  =  -ddx(:rhoYh:*:u: - :Jx:)    - ddy(:rhoYh:*:v: - :Jy:)   - ddz(:rhoYh:*:w: - :Jz:)
    ddt(:rhoYl:)  =  -ddx(:rhoYl:*:u: + :Jx:)    - ddy(:rhoYl:*:v: + :Jy:)   - ddz(:rhoYl:*:w: + :Jz:)
    ddt(:rhou:)   =  -ddx(:rhou:*:u: - :tauxx:)  - ddy(:rhou:*:v: - :tauxy:) - ddz(:rhou:*:w: - :tauxz:) + :rho:*gx
    ddt(:rhov:)   =  -ddx(:rhov:*:u: - :tauxy:)  - ddy(:rhov:*:v: - :tauyy:) - ddz(:rhov:*:w: - :tauyz:)
    ddt(:rhow:)   =  -ddx(:rhow:*:u: - :tauxz:)  - ddy(:rhow:*:v: - :tauyz:) - ddz(:rhow:*:w: - :tauzz:)
    ddt(:Et:)     =  -ddx( (:Et: - :tauxx:)*:u: - :tauxy:*:v: - :tauxz:*:w: - :tx:*:kappa:) - ddy( (:Et: - :tauyy:)*:v: -:tauxy:*:u: - :tauyz:*:w: - :ty:*:kappa:) - ddz( (:Et: - :tauzz:)*:w: - :tauxz:*:u: - :tauyz:*:v: - :tz:*:kappa:) + :rho:*gx*:u:
    # Conservative filter of the EoM
    :rhoYh:     =  fbar( :rhoYh:  )
    :rhoYl:     =  fbar( :rhoYl:  )
    :rhou:      =  fbar( :rhou: )
    :rhov:      =  fbar( :rhov: )
    :rhow:      =  fbar( :rhow: )
    :Et:        =  fbar( :Et:   )
    # Xbar operator
    :mybar: = xbar(:rho:*:u:*:u:)
    # Update the primatives and enforce the EOS
    :rho:       = :rhoYh: + :rhoYl:
    :Yh:        =  :rhoYh: / :rho:
    :Yl:        =  :rhoYl: / :rho:
    :u:         =  :rhou: / :rho:
    :v:         =  :rhov: / :rho:
    :w:         =  :rhow: / :rho:
    :cv:        = :Yh:*CVh + :Yl:*CVl
    :cp:        = :Yh:*CPh + :Yl:*CPl
    :gamma:     = :cp:/:cv:
    :p:         =  ( :Et: - .5*:rho:*(:u:*:u: + :v:*:v:) ) * ( :gamma: - 1.0 )
    :mw:        = 1.0 / ( :Yh: / mwH + :Yl: / mwL )
    :R:         = Runiv / :mw:
    :T:         = :p: / (:rho: * :R: )
    # Artificial bulk viscosity / shear viscosity
    :ux:        =  ddx(:u:)
    :vy:        =  ddy(:v:)
    :wz:        =  ddz(:w:)
    :div:       =  :ux: + :vy: + :wz:
    # Remaining cross derivatives
    :uy:        =  ddy(:u:)
    :uz:        =  ddz(:u:)
    :vx:        =  ddx(:v:)
    :vz:        =  ddz(:v:)
    :wy:        =  ddy(:w:)
    :wx:        =  ddx(:w:)
    :Yx:        =  ddx(:Yh:)
    :Yy:        =  ddy(:Yh:)
    :Yz:        =  ddz(:Yh:)
    :enst:      = sqrt( (:uy:-:vx:)**2 + (:uz: - :wx:)**2 + (:vz:-:wy:)**2 )
    :S:         = sqrt( :ux:*:ux: + :vy:*:vy: + :wz:*:wz: + .5*((:uy:+:vx:)**2 + (:uz: + :wx:)**2 + (:vz:+:wy:)**2) )
    :mu:        = 1.0e-4 * gbar( abs(ring(:S:  )) ) * :rho:
    :beta:      = 7.0e-2 * gbar( abs(ring(:div:)) * :rho: )
    # Artificial species diffusivities
    :Dsgs:      =  1.0e-4 * ring(:Yh:)
    :Ysgs:      =  1.0e2  * (abs(:Yh:) - 1.0 + abs(1.0-:Yh: ) )*gridLen**2
    :adiff:     =  gbar( :rho:*numpy.maximum(:Dsgs:,:Ysgs:) / :dt: )
    :Jx:        =  :adiff:*:Yx:
    :Jy:        =  :adiff:*:Yy:
    :Jz:        =  :adiff:*:Yz:
    :taudia:    =  (:beta:-2./3.*:mu:) *:div: - :p:
    :tauxx:     =  2.0*:mu:*:ux:   + :taudia:
    :tauyy:     =  2.0*:mu:*:vy:   + :taudia:
    :tauzz:     =  2.0*:mu:*:wz:   + :taudia:
    :tauxy:     = :mu:*(:uy:+:vx:) 
    :tauxz:     = :mu:*(:uz:+:wx:) 
    :tauyz:     = :mu:*(:vz:+:wz:) 
    [:tx:,:ty:,:tz:] = grad(:T:)
    :kappa:     = 1.0e-3 * gbar( ring(:T:)* :rho:*:cv:/(:T: * :dt: ) )
    :cs:        = sqrt( :p: / :rho: * :gamma: )
    # Time step control routines
    :dt:        = dt.courant(:u:,:v:,:w:,:cs:)*1.0
    :dt:        = numpy.minimum(:dt:,0.2 * dt.diff(:beta:,:rho:))
    :dt:        = numpy.minimum(:dt:,0.2 * dt.diff(:mu:,:rho:))
    :dt:        = numpy.minimum(:dt:,0.2 * dt.diff(:adiff:,:rho:))
    # Add some BCs in the x-direction
    bc.const(['Yh'],['xn'],1.0)
    bc.const(['Yh'],['x1'],0.0)
    bc.const(['Yl'],['x1'],1.0)
    bc.const(['Yl'],['xn'],0.0)
    bc.extrap(['rho','Et'],['x1','xn'])
    bc.const(['u','v','w'],['x1','xn'],0.0)
    # Sponge BCs
    :leftBC:  = 1.0 - 0.5 * (1.0 + tanh( (meshx-1.0) / .1 ) )
    :rightBC: = 0.5 * (1.0 + tanh( (meshx-8.0) / .1 ) )
    :BC: = numpy.maximum(:leftBC:,:rightBC:)
    :u: = gbar(:u:)*:BC: + :u:*(1.0 - :BC:)
    :rho: = gbar(:rho:)*:BC: + :rho:*(1.0 - :BC:)
    :Et: = gbar(:Et:)*:BC: + :Et:*(1.0 - :BC:)
    :rhoYh: = :rho:*:Yh:
    :rhoYl: = :rho:*:Yl:
    :rhou: = :rho:*:u:
    :rhov: = :rho:*:v:
    :rhow: = :rho:*:w:
    :mix:  = 4.0*:Yh:*:Yl:
    """

    # Add the EOM to the solver
    ss.EOM(textwrap.dedent(eom), parm_dict)

    # Initialize variables
    ic_vel = """
    :gamma:= 5./3.
    p0     = 1.0
    At     = ( (rho_h - rho_l)/(rho_h + rho_l) )
    # NOTE: WHY THIS PARTICULAR FRACTION OF THE RT GROWTH RATE?
    u0     = sqrt( abs(gx*At/waveLength) ) * .1

    # Add interface
    # NOTE: diffuse interface?
    :Yl: = .5 * (1.0-tanh( sqrt(pi)*( meshx - 1.4*pi ) / delta ))
    :Yh: = 1.0 - :Yl:
    :p:  += p0 

    # Add oscillations near interface
    wgt = 4*:Yh:*:Yl:
    :v: *= 0.0
    :w: *= 0.0
    # NOTE: what is gbar?
    :u: = wgt * gbar( (random3D()-0.5)*u0 )

    :rho:       = rho_h * :Yh: + rho_l * :Yl:
    :cv:        = :Yh:*CVh + :Yl:*CVl
    :cp:        = :Yh:*CPh + :Yl:*CPl
    :gamma:     = :cp:/:cv:
    :mw:        = 1.0 / ( :Yh: / mwH + :Yl: / mwL )
    :R:         = Runiv / :mw:
    :T:         = :p: / (:rho: * :R: )

    # Form conserved quatities
    :rhoYh: = :rho:*:Yh:
    :rhoYl: = :rho:*:Yl:
    :rhou: = :rho:*:u:
    :rhov: = :rho:*:v:
    :rhow: = :rho:*:w:
    :Et:  = :p: / (:gamma:-1.0) + 0.5*:rho:*(:u:*:u: + :v:*:v: + :w:*:w:)
    :cs:  = sqrt( :p: / :rho: * :gamma: )
    :dt: = dt.courant(:u:,:v:,:w:,:cs:)
    """

    # Velocity free/shape only interface perturbatiosn
    ic_shape = """
    :gamma:= 5./3.
    p0     = 1.0
    At     = ( (rho_h - rho_l)/(rho_h + rho_l) )
    u0     = sqrt( abs(gx*At/waveLength) ) * .1  # NOTE: WHY THIS PARTICULAR FRACTION OF THE RT GROWTH RATE?

    # Perturbation: fixed single mode sinusoids
    Amp = 3.5 + 0.05*(sin(meshy*waveLength) + cos(meshz*waveLength))
    # Add interface
    :Yl: = 0.5 * (1.0 - tanh( sqrt(pi)*( meshx - Amp) / delta))
    :Yh: = 1.0 - :Yl:
    :p:  += p0 

    # Add oscillations near interface
    wgt = 4*:Yh:*:Yl:
    :v: *= 0.0
    :w: *= 0.0
    :u: *= 0.0

    :rho:       = rho_h * :Yh: + rho_l * :Yl:
    :cv:        = :Yh:*CVh + :Yl:*CVl
    :cp:        = :Yh:*CPh + :Yl:*CPl
    :gamma:     = :cp:/:cv:
    :mw:        = 1.0 / ( :Yh: / mwH + :Yl: / mwL )
    :R:         = Runiv / :mw:
    :T:         = :p: / (:rho: * :R: )

    # Form conserved quatities
    :rhoYh: = :rho:*:Yh:
    :rhoYl: = :rho:*:Yl:
    :rhou: = :rho:*:u:
    :rhov: = :rho:*:v:
    :rhow: = :rho:*:w:
    :Et:  = :p: / (:gamma:-1.0) + 0.5*:rho:*(:u:*:u: + :v:*:v: + :w:*:w:)
    :cs:  = sqrt( :p: / :rho: * :gamma: )
    :dt: = dt.courant(:u:,:v:,:w:,:cs:)
    """
    # Set the initial conditions
    numpy.random.seed(random_ic_seed)  # 1234 was previous default

    # INSERT SWITCHYARD FOR ALTERNATE IC'S WHEN THEY'RE WORKING
    ss.setIC(textwrap.dedent(ic_vel), parm_dict)

    # Write a time loop
    time = 0.0

    # Start time loop
    CFL = 1.0
    dt = ss.variables["dt"].data * CFL

    # Viz/IO
    viz_freq = 20
    dmp_freq = 200

    tstop = 100.0
    dtmax = dt * 0.1

    outVars = ["p", "u", "v", "w", "rho", "Yh"]
    ss.write(outVars)

    mixW = []
    timeW = []

    while time < tstop:

        # Update the EOM and get next dt
        time = ss.rk4(time, dt)
        dt = ss.variables["dt"].data * CFL
        dt = min(dt, dtmax * 1.1)
        dtmax = dt * 1.0

        umax = ss.var("u").mean()
        ss.iprint("%s -- %s --- Umax: %s " % (ss.cycle, time, umax))

        if ss.cycle % viz_freq == 0:
            mixW.append(
                numpy.trapz(ss.var("mix").mean(axis=[1, 2]), ss.var("meshx")[:, 0, 0])
            )
            timeW.append(time)



        if ss.cycle % dmp_freq == 0:
            ss.write(outVars)

        if not headless:
            if ss.cycle % viz_freq == 0:

                # 2D contour plots
                ss.plot.figure(1)
                ss.plot.clf()
                ss.plot.contourf("rho", 32, cmap="turbo")

                ss.plot.figure(2)
                ss.plot.clf()
                ss.plot.plot("mix", label="Mixing width")

            if ss.PyMPI.master:
                # NOTE: built in plot function expects a mesh plot.  vars vs time need
                # to fall back to raw matplotlib, and limiting it only to master mpi rank
                # NOTE: add the RT alpha growth rate ~solution for comparison?
                plt.figure(3)
                plt.plot(timeW, mixW)
                plt.xlabel('time')
                plt.ylabel('mixing width')
                plt.pause(0.01)

    # Save the mixing width curve data
    fname = problem + ".dat"
    header = f"# 'time' 'mixing width'"
    numpy.savetxt(fname, (timeW, mixW), header=header)
    print(f"Saved mixing width vs time curve to '{fname}'")  # Add more formal logger output?


def setup_argparse():
    parser = argparse.ArgumentParser(
        prog="PyrandaRT",
        description="A configurable model of miscible Rayleigh-Taylor mixing using Pyranda",
    )

    # parser.add_argument(
    #     "-m",
    #     "--mesh-res",
    #     type=int,
    #     default=64,
    #     help="Mesh resolution to use, in terms of zones per cm, uniform in x, y, z.",
    # )

    # NOTE: maybe nice for options to have mutually exclusive arg sets, one for single density + Atwood,
    # and another for two densities and no Atwood..
    parser.add_argument(
        "-a",
        "--atwood-number",
        type=float,
        default=0.5,
        help="Atwood number to use for the simulation (density ratio).  Valid range is [0, 1]",
    )

    parser.add_argument(
        "-l",
        "--light-density",
        type=float,
        default=1.0,
        help="Density of the lighter fluid to use.  Heavy fluid determined via the Atwood number",
    )

    parser.add_argument(
        "-d",
        "--dim",
        type=str,
        choices={"2D", "3D"},
        default="2D",
        help="Dimensionality of the simulation to run",
    )

    parser.add_argument(
        "-n",
        "--num-points",
        type=int,
        default=64,
        help="Number of points in the y direction. x computed to ~uniform grid size.",
    )

    parser.add_argument(
        "--initial-condition",
        type=str,
        choices={"random-velocity"},
        default="random-velocity",
        help="Initial condition to run.",
    )

    parser.add_argument(
        '-s',
        '--seed',
        type=int,
        # default=1234,
        help="Seed to use in random number generator"
    )

    parser.add_argument(
        '-t',
        '--tstop',
        default=100.0,
        help="Simulation time to run to in units of"
    )
    # add flag for dtmax fraction?
    
    # Output controls
    parser.add_argument(
        '--viz-freq-cycle',
        type=int,
        default=20,
        help="Cycle intervals at which to dump scalar curve data."
    )

    parser.add_argument(
        '--dump-freq-cycle',
        type=int,
        default=200,
        help="Cycle intervals at which to dump mesh structured viz data (visit)."
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help="Turn on headless mode to hide interactive plots"
    )
    
    # Potential other interesting args:
    # Problem name -> this controls output dir?
    # domain size (x, y, z), npts x, y, z
    # scaling factor on initial growth rate/velocity -> wavelength used here, but not for shape??
    # Dump pngs from matplotlib for easier movie automation?  -> does slow down sim a bit; may
    #      need to optimize the pyrandaplot funcs to append data instead of blowing away each frame
    return parser


def main():
    parser = setup_argparse()

    args = parser.parse_args()

    try:
        run_sim(args)
    except Exception:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())