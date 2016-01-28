// Copyright (c) 2014 Daniel Kraft
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "script/names.h"

#include "uint256.h"

CNameScript::CNameScript (const CScript& script)
  : op(OP_NOP), address(script)
{
  opcodetype nameOp;
  CScript::const_iterator pc = script.begin ();
  if (!script.GetOp (pc, nameOp))
    return;

  opcodetype opcode;
  while (true)
    {
      valtype vch;

      if (!script.GetOp (pc, opcode, vch))
        return;
      if (opcode == OP_DROP || opcode == OP_2DROP || opcode == OP_NOP)
        break;
      if (!(opcode >= 0 && opcode <= OP_PUSHDATA4))
        return;

      args.push_back (vch);
    }

  // Move the pc to after any DROP or NOP.
  while (opcode == OP_DROP || opcode == OP_2DROP || opcode == OP_NOP)
    if (!script.GetOp (pc, opcode))
      break;
  pc--;

  /* Now, we have the args and the operation.  Check if we have indeed
     a valid name operation and valid argument counts.  Only now set the
     op and address members, if everything is valid.  */
  switch (nameOp)
    {
    case OP_NAME_NEW:
      if (args.size () != 1)
        return;
      break;

    case OP_NAME_FIRSTUPDATE:
      if (args.size () != 3)
        return;
      break;

    case OP_NAME_UPDATE:
      if (args.size () != 2)
        return;
      break;

    default:
      return;
    }

  op = nameOp;
  
  CScript::const_iterator pcAddress = pc;
  
  // Ops that have a value field may receive extensions.
  // This doesn't affect consensus rules in any way.
  if(op == OP_NAME_FIRSTUPDATE || op == OP_NAME_UPDATE)
  {
    args.push_back(args[args.size()-1]);
    
    while(true)
    {
      opcodetype nameExtOp, nameExtDropOp;
      valtype vch;
      
      if (!script.GetOp (pc, nameExtOp))
      {
	break;
      }
      
      if (! (nameExtOp == op) )
      {
	break;
      }
      
      opcodetype pushOp;
      
      if (!script.GetOp (pc, pushOp, vch))
      {
	break;
      }
      
      if (!(pushOp >= 0 && pushOp <= OP_PUSHDATA4))
      {
	break;
      }
      
      if (!script.GetOp (pc, nameExtDropOp))
      {
	break;
      }
      
      if (! (nameExtDropOp == OP_2DROP) )
      {
	break;
      }
      
      args[args.size()-1].insert(args[args.size()-1].end(), vch.begin(), vch.end());
      pcAddress = pc;
    }
  }
  
  address = CScript (pcAddress, script.end ());
}

CScript
CNameScript::buildNameNew (const CScript& addr, const uint160& hash)
{
  CScript prefix;
  prefix << OP_NAME_NEW << ToByteVector (hash) << OP_2DROP;

  return prefix + addr;
}

CScript
CNameScript::buildNameFirstupdate (const CScript& addr, const valtype& name,
                                   const valtype& value, const valtype& rand)
{
  CScript prefix;
  
  if(value.size() <= MAX_SCRIPT_ELEMENT_SIZE)
  {
    prefix << OP_NAME_FIRSTUPDATE << name << rand << value
           << OP_2DROP << OP_2DROP;
  }
  else
  {
    valtype value1(value.begin(), value.begin() + MAX_SCRIPT_ELEMENT_SIZE);
    
    prefix << OP_NAME_FIRSTUPDATE << name << rand << value1
           << OP_2DROP << OP_2DROP;
    
    size_t valueStep = MAX_SCRIPT_ELEMENT_SIZE;
    while(value.size() > valueStep + MAX_SCRIPT_ELEMENT_SIZE)
    {
      valtype value2(value.begin() + valueStep, value.begin() + valueStep + MAX_SCRIPT_ELEMENT_SIZE);
      prefix << OP_NAME_FIRSTUPDATE << value2 << OP_2DROP;
    }
    
    if(value.size() > valueStep)
    {
      valtype value2(value.begin() + valueStep, value.end());
      prefix << OP_NAME_FIRSTUPDATE << value2 << OP_2DROP;
    }
  }

  return prefix + addr;
}

CScript
CNameScript::buildNameUpdate (const CScript& addr, const valtype& name,
                              const valtype& value)
{
  CScript prefix;
  
  if(value.size() <= MAX_SCRIPT_ELEMENT_SIZE)
  {
    prefix << OP_NAME_UPDATE << name << value << OP_2DROP << OP_DROP;
  }
  else
  {
    valtype value1(value.begin(), value.begin() + MAX_SCRIPT_ELEMENT_SIZE);
    
    prefix << OP_NAME_UPDATE << name << value1 << OP_2DROP << OP_DROP;
  
    size_t valueStep = MAX_SCRIPT_ELEMENT_SIZE;
    while(value.size() > valueStep + MAX_SCRIPT_ELEMENT_SIZE)
    {
      valtype value2(value.begin() + valueStep, value.begin() + valueStep + MAX_SCRIPT_ELEMENT_SIZE);
      prefix << OP_NAME_UPDATE << value2 << OP_2DROP;
    }
    
    if(value.size() > valueStep)
    {
      valtype value2(value.begin() + valueStep, value.end());
      prefix << OP_NAME_UPDATE << value2 << OP_2DROP;
    }
  }

  return prefix + addr;
}
