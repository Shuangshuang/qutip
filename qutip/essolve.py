# This file is part of QuTiP.
#
#    QuTiP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    QuTiP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with QuTiP.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2011 and later, Paul D. Nation & Robert J. Johansson
#
###########################################################################


import numpy as np
from qutip.qobj import Qobj
from qutip.eseries import eseries, estidy, esval
from qutip.expect import expect
from qutip.superoperator import *
from qutip.odedata import Odedata

# -----------------------------------------------------------------------------
# pass on to wavefunction solver or master equation solver depending on whether
# any collapse operators were given.
#
def essolve(H, rho0, tlist, c_op_list, e_ops):
    """
    Evolution of a state vector or density matrix (`rho0`) for a given
    Hamiltonian (`H`) and set of collapse operators (`c_op_list`), by
    expressing the ODE as an exponential series. The output is either
    the state vector at arbitrary points in time (`tlist`), or the
    expectation values of the supplied operators (`e_ops`).

    Parameters
    ----------
    H : qobj/function_type
        System Hamiltonian.

    rho0 : :class:`qutip.qobj`
        Initial state density matrix.

    tlist : list/array
        ``list`` of times for :math:`t`.

    c_op_list : list of :class:`qutip.qobj`
        ``list`` of :class:`qutip.qobj` collapse operators.

    e_ops : list of :class:`qutip.qobj`
        ``list`` of :class:`qutip.qobj` operators for which to evaluate
        expectation values.


    Returns
    -------
     expt_array : array
        Expectation values of wavefunctions/density matrices for the
        times specified in ``tlist``.


    .. note:: This solver does not support time-dependent Hamiltonians.

    """
    n_expt_op = len(e_ops)
    n_tsteps = len(tlist)

    # Calculate the Liouvillian
    if (c_op_list is None or len(c_op_list) == 0) and isket(rho0):
        L = H
    else:
        L = liouvillian(H, c_op_list)

    es = ode2es(L, rho0)

    # evaluate the expectation values
    if n_expt_op == 0:
        result_list = [Qobj()] * n_tsteps # XXX
    else:
        result_list = np.zeros([n_expt_op, n_tsteps], dtype=complex)

    for n, e in enumerate(e_ops):
        result_list[n, :] = expect(e, esval(es, tlist))

    data = Odedata()
    data.solver = "essolve"
    data.times = tlist
    data.expect = [np.real(result_list[n, :]) if e.isherm else result_list[n, :]
                   for n, e in enumerate(e_ops)]

    return data


# -----------------------------------------------------------------------------
#
#
def ode2es(L, rho0):
    """Creates an exponential series that describes the time evolution for the
    initial density matrix (or state vector) `rho0`, given the Liouvillian
    (or Hamiltonian) `L`.

    Parameters
    ----------
    L : qobj
        Liouvillian of the system.

    rho0 : qobj
        Initial state vector or density matrix.

    Returns
    -------
    eseries : :class:`qutip.eseries`
        ``eseries`` represention of the system dynamics.

    """

    if issuper(L):

        # check initial state
        if isket(rho0):
            # Got a wave function as initial state: convert to density matrix.
            rho0 = rho0 * rho0.dag()

        w, v = L.eigenstates()
        v = np.hstack([ket.full() for ket in v])
        # w[i]   = eigenvalue i
        # v[:,i] = eigenvector i

        rlen = prod(rho0.shape)
        r0 = mat2vec(rho0.full())
        v0 = la.solve(v, r0)
        vv = v * sp.spdiags(v0.T, 0, rlen, rlen)

        out = None
        for i in range(rlen):
            qo = Qobj(vec2mat(vv[:, i]), dims=rho0.dims, shape=rho0.shape)
            if out:
                out += eseries(qo, w[i])
            else:
                out = eseries(qo, w[i])

    elif isoper(L):

        if not isket(rho0):
            raise TypeError('Second argument must be a ket if first' +
                            'is a Hamiltonian.')

        w, v = L.eigenstates()
        v = np.hstack([ket.full() for ket in v])
        # w[i]   = eigenvalue i
        # v[:,i] = eigenvector i

        rlen = prod(rho0.shape)
        r0 = rho0.full()
        v0 = la.solve(v, r0)
        vv = v * sp.spdiags(v0.T, 0, rlen, rlen)

        out = None
        for i in range(rlen):
            qo = Qobj(np.matrix(vv[:, i]).T, dims=rho0.dims, shape=rho0.shape)
            if out:
                out += eseries(qo, -1.0j * w[i])
            else:
                out = eseries(qo, -1.0j * w[i])

    else:
        raise TypeError('First argument must be a Hamiltonian or Liouvillian.')

    return estidy(out)
