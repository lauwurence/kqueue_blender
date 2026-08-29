settings
{
	priority=1
	exclude.where = !process.is_explorer
	showdelay = 200
	// Options to allow modification of system items
	modify.remove.duplicate=1
	tip.enabled=true
}

import 'imports/theme.nss'
import 'imports/images.nss'

import 'imports/modify.nss'

menu(mode="multiple" title="Pin/Unpin" image=icon.pin)
{
}

$working_dir = 'F:\RenPy\00_Renders\kqueue_blender\webm\'

menu(type='file|dir' mode="multiple" title='Convert to WebM' image='cmd.exe' pos=1)
{
	item(
		title='Preset "1080p"'
		cmd=working_dir + '.webm - 1080p.bat'
		dir=working_dir
		arg='@sel.path'
		image='cmd.exe'
		pos=0)

	item(
		title='Preset "android"'
		cmd=working_dir + '.webm - android.bat'
		dir=working_dir
		arg='@sel.path'
		image='cmd.exe'
		pos=1)

	item(
		title='Preset "2160p"'
		cmd=working_dir + '.webm - 2160p.bat'
		dir=working_dir
		arg='@sel.path'
		image='cmd.exe'
		pos=2)

	item(
		title='Preset "ALL"'
		cmd=working_dir + '.webm - all.bat'
		dir=working_dir
		arg='@sel.path'
		image='cmd.exe'
		pos=3)

	item(
		title='Create "settings.json"'
		cmd=working_dir + 'create_settings.bat'
		dir=working_dir
		arg='@sel.path'
		image='.json'
		pos=4)

}
